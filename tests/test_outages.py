"""Tests for parsing and matching the feed."""

from __future__ import annotations

from datetime import timedelta
from zoneinfo import ZoneInfo

from custom_components.deer_outages.outages import (
    TYPE_INCIDENT,
    Outage,
    normalize,
    normalize_locality,
    parse_incidents,
    parse_planned,
    select,
    split_streets,
)

from .conftest import load

TZ = ZoneInfo("Europe/Bucharest")


def _all():
    return parse_planned(load("scheduled.json"), TZ) + parse_incidents(
        load("incidents.json"), TZ, timedelta(hours=2)
    )


def test_normalize() -> None:
    """Accents, punctuation and shorthands do not matter."""
    assert normalize("Tg. Secuiesc") == "TARGU SECUIESC"
    assert normalize("TÂRGU-SECUIESC") == "TARGU SECUIESC"
    assert normalize("Gábor Áron") == "GABOR ARON"
    assert normalize("Ștefan cel Mare") == "STEFAN CEL MARE"
    assert normalize_locality("Kézdivásárhely") == "TARGU SECUIESC"
    assert normalize_locality("Sepsiszentgyörgy") == "SFANTU GHEORGHE"
    assert split_streets("Gábor Áron, Ady Endre;\nKossuth Lajos,") == [
        "Gábor Áron",
        "Ady Endre",
        "Kossuth Lajos",
    ]


def test_parse_planned() -> None:
    """Rows of one work become one outage with every street once."""
    planned = parse_planned(load("scheduled.json"), TZ)
    work = next(o for o in planned if o.work_id == "50001")
    assert [p.text for p in work.places] == [
        "TARGU SECUIESC, Strada GABOR ARON",
        "TARGU SECUIESC, Strada ADY ENDRE",
    ]
    assert work.start.isoformat() == "2026-11-06T10:00:00+02:00"
    assert work.end.isoformat() == "2026-11-06T14:00:00+02:00"
    assert work.duration == "4h : 0'"
    assert not work.places[0].is_area

    village = next(o for o in planned if o.work_id == "45684")
    assert village.places[0].localities == ["LIVEZILE", "IZVOARELE"]
    assert village.places[0].is_area
    zone = next(o for o in planned if o.work_id == "50003")
    assert zone.places[0].is_area


def _planned(text: str) -> Outage:
    """Return one parsed planned outage for the given address line."""
    return parse_planned(
        [
            {
                "id": "90001",
                "judet": "Alba",
                "ansambluFunctional": text,
                "dataProgramareStart": "10/11/2026 08:00",
                "dataProgramareStop": "10/11/2026 12:00",
            }
        ],
        TZ,
    )[0]


def test_parse_planned_village() -> None:
    """The village after the commune becomes part of the locality.

    The real feed writes villages both as "COMUNA, SAT(COMUNA), ..." and as
    "COMUNA, SAT, Strada ..." (plain comma); either spelling must match when
    the locality is configured as the commune or as the village.
    """
    outage = _planned("ARIESENI, CASA DE PIATRA, Strada  PRINCIPALA")
    place = outage.places[0]
    assert place.locality == "ARIESENI CASA DE PIATRA"
    assert place.detail == "Strada  PRINCIPALA"
    assert not place.is_area

    assert select([outage], "Alba", "Casa de Piatra", [])
    assert select([outage], "Alba", "Arieșeni", [])

    assert _planned("IGHIU, SARD, Strada  PRINCIPALA PARTIAL").places[0].locality == ("IGHIU SARD")
    assert _planned("RECEA, DEJANI, sat  sat").places[0].locality == "RECEA DEJANI"
    assert _planned("PETELEA, HABIC, Strada  HABIC").places[0].locality == ("PETELEA HABIC")


def test_parse_planned_village_not_street() -> None:
    """A street line is not mistaken for a village."""
    outage = _planned("TARGU MURES, Strada  REVOLUTIEI 49,51")
    place = outage.places[0]
    assert place.locality == "TARGU MURES"
    assert place.detail == "Strada  REVOLUTIEI 49,51"
    assert not place.is_area
    assert select([outage], "Alba", "Târgu Mureș", [])

    zone = _planned("CRISTIAN, ZONA  PT 14 CINDRELUL").places[0]
    assert zone.locality == "CRISTIAN"
    assert zone.is_area


def test_parse_incidents() -> None:
    """Incident addresses are split per line, a missing end gets a default."""
    incident = next(
        o
        for o in parse_incidents(load("incidents.json"), TZ, timedelta(hours=2))
        if o.work_id == "70001"
    )
    assert incident.kind == TYPE_INCIDENT
    assert not incident.end_known
    assert incident.end - incident.start == timedelta(hours=2)
    assert [(p.locality, p.detail) for p in incident.places] == [
        ("TARGU SECUIESC TARGU SECUIESC", "Strada GABOR ARON"),
        ("TARGU SECUIESC TARGU SECUIESC", "Strada KOSSUTH LAJOS"),
    ]


def test_select_street() -> None:
    """A street matches its lines, zones of the town, never other towns."""
    found = select(_all(), "Covasna", "Kézdivásárhely", ["Gábor Áron"])
    assert {(o.work_id, tuple(p.text for p in places)) for o, places in found} == {
        ("50001", ("TARGU SECUIESC, Strada GABOR ARON",)),
        ("50003", ("TARGU SECUIESC, ZONA PT 7 FABRICII",)),
        ("70001", ("Loc: TARGU SECUIESC, Sat: TARGU SECUIESC, Str.: GABOR ARON",)),
    }


def test_select_whole_locality() -> None:
    """Without streets every outage of the locality matches."""
    found = select(_all(), "Covasna", "Târgu Secuiesc", [])
    assert sorted(o.work_id for o, _ in found) == ["50001", "50002", "50003", "70001"]


def test_select_street_words() -> None:
    """A street matches only its own lines, plus whole-locality lines.

    Whole words are compared: "Curtea" matches "Strada CURTEA 5" but a street
    typed as "Aron" would not match "Strada GABOR ARON".
    """
    found = select(_all(), "Covasna", "Targu Secuiesc", ["Curtea"])
    assert [(o.work_id, tuple(p.text for p in places)) for o, places in found] == [
        ("50002", ("TARGU SECUIESC, Strada CURTEA 5",)),
        ("50003", ("TARGU SECUIESC, ZONA PT 7 FABRICII",)),
    ]


def test_select_other_county() -> None:
    """The county has to match too."""
    assert select(_all(), "Harghita", "Targu Secuiesc", []) == []


def test_village_names() -> None:
    """A village is found in the middle of the address, a street name is not a town."""
    records = [
        {"id": "1", "judet": "Buzau", "ansambluFunctional": "POGOANELE, VALEA SALCIILOR, Strada  PRINCIPALA",
         "dataProgramareStart": "07/11/2026 09:00", "dataProgramareStop": "07/11/2026 12:00"},
        {"id": "2", "judet": "Buzau", "ansambluFunctional": "BUZAU, Strada  VALEA SALCIILOR",
         "dataProgramareStart": "07/11/2026 09:00", "dataProgramareStop": "07/11/2026 12:00"},
    ]
    outages = parse_planned(records, TZ)
    assert [o.work_id for o, _ in select(outages, "Buzau", "Valea Sălciilor", [])] == ["1"]
    assert [o.work_id for o, _ in select(outages, "Buzau", "Pogoanele", [])] == ["1"]
    assert [o.work_id for o, _ in select(outages, "Buzau", "Pogoanele", ["Principala"])] == ["1"]
