"""Turn the DEER feed into outages and pick the ones that concern one address.

Kept free of Home Assistant objects so it is easy to test.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timedelta, tzinfo
from typing import Any

TYPE_PLANNED = "planned"
TYPE_INCIDENT = "incident"

_ABBREVIATIONS = {"TG": "TARGU", "SF": "SFANTU", "SFT": "SFANTU", "STR": "STRADA"}
_STREET_WORDS = {
    "STRADA",
    "STRADA:",
    "ALEEA",
    "BULEVARDUL",
    "BD",
    "CALEA",
    "CALE",
    "PIATA",
}
# Markers in a planned outage address that it covers more than single streets.
_AREA_MARKERS = ("LOCALITATE", "SAT", "ZONA", "PT")
_BR = re.compile(r"<br\s*/?>", re.IGNORECASE)

# Hungarian names of towns in the DEER area, so either name can be typed in.
LOCALITY_ALIASES = {
    "KEZDIVASARHELY": "TARGU SECUIESC",
    "SEPSISZENTGYORGY": "SFANTU GHEORGHE",
    "KOVASZNA": "COVASNA",
    "BAROT": "BARAOLT",
    "BERECK": "BRETCU",
    "CSIKSZEREDA": "MIERCUREA CIUC",
    "SZEKELYUDVARHELY": "ODORHEIU SECUIESC",
    "GYERGYOSZENTMIKLOS": "GHEORGHENI",
    "SZEKELYKERESZTUR": "CRISTURU SECUIESC",
    "MAROSVASARHELY": "TARGU MURES",
    "BRASSO": "BRASOV",
    "KOLOZSVAR": "CLUJ NAPOCA",
    "NAGYSZEBEN": "SIBIU",
    "GYULAFEHERVAR": "ALBA IULIA",
}


def normalize_locality(text: str | None) -> str:
    """Normalize a locality, turning a known Hungarian name into the Romanian one."""
    plain = normalize(text)
    return LOCALITY_ALIASES.get(plain.replace(" ", ""), plain)


def normalize(text: str | None) -> str:
    """Upper case, without accents or punctuation, with common shorthands expanded.

    "Tg. Secuiesc" and "TÂRGU SECUIESC" both become "TARGU SECUIESC", and
    "Gábor Áron utca" becomes "GABOR ARON UTCA".
    """
    if not text:
        return ""
    decomposed = unicodedata.normalize("NFKD", text)
    plain = "".join(c for c in decomposed if not unicodedata.combining(c))
    # Romanian letters with a comma or cedilla below are not always split by NFKD.
    plain = plain.translate(str.maketrans("ȘșŞşȚțŢţ", "SsSsTtTt"))
    words = re.sub(r"[^0-9A-Za-z]+", " ", plain).upper().split()
    return " ".join(_ABBREVIATIONS.get(word, word) for word in words)


def _contains_words(haystack: str, needle: str) -> bool:
    """Return if the words of needle appear together in haystack."""
    return bool(needle) and f" {needle} " in f" {haystack} "


def parse_time(value: Any, tz: tzinfo) -> datetime | None:
    """Parse "dd/mm/yyyy HH:MM" in the feed time zone."""
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.strptime(value.strip(), "%d/%m/%Y %H:%M").replace(tzinfo=tz)
    except ValueError:
        return None


@dataclass
class Place:
    """One address line of an outage."""

    locality: str
    detail: str
    text: str

    @property
    def is_area(self) -> bool:
        """Return if the line covers a whole locality, village or zone."""
        words = normalize(self.detail).split()
        return (
            not words
            or words[0] in _AREA_MARKERS
            or (not any(word in _STREET_WORDS for word in words))
        )


@dataclass
class Outage:
    """A planned outage or an incident, with every address it touches."""

    key: str
    kind: str
    work_id: str
    county: str
    start: datetime
    end: datetime
    end_known: bool
    duration: str | None = None
    level: str | None = None
    places: list[Place] = field(default_factory=list)

    def matching_places(self, locality: str, streets: list[str]) -> list[Place]:
        """Return the places of this outage at the given locality and streets.

        Without streets every place in the locality matches. With streets, a
        street line matches only if it names one of them, while lines covering
        the whole locality or a zone always match, since they may include it.
        """
        wanted_locality = normalize_locality(locality)
        wanted_streets = [normalize(street) for street in streets if normalize(street)]
        found: list[Place] = []
        for place in self.places:
            if not _contains_words(normalize(place.locality), wanted_locality):
                continue
            if not wanted_streets or place.is_area:
                found.append(place)
                continue
            detail = normalize(place.detail)
            if any(_contains_words(detail, street) for street in wanted_streets):
                found.append(place)
        return found


def _county_of(record: dict[str, Any]) -> str:
    county = record.get("judet") or record.get("sucursala") or ""
    if county.upper().startswith("SDEE "):
        county = county[5:]
    return county


def _is_address_marker(value: str) -> bool:
    """Return if a village candidate is really a street or an area marker."""
    words = normalize(value).split()
    return not words or words[0] in _STREET_WORDS or words[0] in _AREA_MARKERS


def _split_planned(text: str) -> Place:
    """Split "LOCALITY, rest" from a planned outage."""
    locality, _, detail = text.partition(",")
    detail = detail.strip()
    # "LIVEZILE, IZVOARELE(LIVEZILE), Sat ..." names the village before the
    # "(" and "ARIESENI, CASA DE PIATRA, Strada ..." after a plain comma.
    village = re.match(r"^([^,(]+)\([^)]*\)\s*,", detail) or re.match(r"^([^,]+),", detail)
    if village and _is_address_marker(village.group(1)):
        village = None
    if village:
        locality = f"{locality} {village.group(1)}"
        detail = detail[village.end() :].strip(" ,")
    return Place(locality=locality.strip(), detail=detail, text=" ".join(text.split()))


def _split_incident(text: str) -> Place:
    """Split "Loc: X, Sat: Y, Strada: Z, Nr: 1" from an incident."""
    parts: dict[str, str] = {}
    for chunk in text.split(","):
        name, sep, value = chunk.partition(":")
        if sep:
            parts[normalize(name)] = value.strip()
    locality = " ".join(value for value in (parts.get("LOC"), parts.get("SAT")) if value)
    street = parts.get("STRADA") or ""
    detail = f"Strada {street}" if street else ""
    if number := parts.get("NR"):
        detail = f"{detail} {number}".strip()
    return Place(locality=locality, detail=detail, text=" ".join(text.split()))


def parse_planned(records: list[dict[str, Any]], tz: tzinfo) -> list[Outage]:
    """Group the per-street rows of planned outages into outages."""
    outages: dict[str, Outage] = {}
    for record in records:
        start = parse_time(record.get("dataProgramareStart"), tz)
        end = parse_time(record.get("dataProgramareStop"), tz)
        text = record.get("ansambluFunctional")
        if start is None or not isinstance(text, str) or not text.strip():
            continue
        key = f"{TYPE_PLANNED}-{record.get('id')}-{start.isoformat()}"
        outage = outages.get(key)
        if outage is None:
            outage = outages[key] = Outage(
                key=key,
                kind=TYPE_PLANNED,
                work_id=str(record.get("id")),
                county=_county_of(record),
                start=start,
                end=end or start,
                end_known=end is not None,
                duration=record.get("durataProgramare") or None,
                level=record.get("nivel") or None,
            )
        place = _split_planned(text)
        if place.text not in {p.text for p in outage.places}:
            outage.places.append(place)
    return sorted(outages.values(), key=lambda o: (o.start, o.key))


def parse_incidents(
    records: list[dict[str, Any]], tz: tzinfo, default_duration: timedelta
) -> list[Outage]:
    """Turn incidents, each with one or more addresses, into outages."""
    outages: list[Outage] = []
    for record in records:
        start = parse_time(record.get("dataStart"), tz)
        text = record.get("adresa")
        if start is None or not isinstance(text, str):
            continue
        end = parse_time(record.get("dataStop"), tz)
        places = [_split_incident(line) for line in _BR.split(text) if line.strip()]
        outages.append(
            Outage(
                key=f"{TYPE_INCIDENT}-{record.get('id')}",
                kind=TYPE_INCIDENT,
                work_id=str(record.get("id")),
                county=_county_of(record),
                start=start,
                end=end or start + default_duration,
                end_known=end is not None,
                places=places,
            )
        )
    return sorted(outages, key=lambda o: (o.start, o.key))


def select(
    outages: list[Outage], county: str, locality: str, streets: list[str]
) -> list[tuple[Outage, list[Place]]]:
    """Return the outages in the county that touch the locality and streets."""
    wanted_county = normalize(county)
    selected = []
    for outage in outages:
        if normalize(outage.county) != wanted_county:
            continue
        if places := outage.matching_places(locality, streets):
            selected.append((outage, places))
    return selected


def split_streets(value: str | None) -> list[str]:
    """Split a comma or semicolon separated street list."""
    return [part.strip() for part in re.split(r"[,;\n]", value or "") if part.strip()]
