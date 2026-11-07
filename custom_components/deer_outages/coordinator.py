"""Polling, filtering and new outage detection for the DEER integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import DeerApiError
from .const import (
    CONF_COUNTY,
    CONF_LOCALITY,
    CONF_STREETS,
    COUNTIES,
    DOMAIN,
    EVENT_NEW_OUTAGE,
    FEED_TIME_ZONE,
    INCIDENT_DEFAULT_DURATION,
    INCIDENT_ONGOING_EXTENSION,
    MAX_DATA_AGE,
    SCAN_INTERVAL,
    SEEN_RETENTION_DAYS,
    STORAGE_VERSION,
)
from .feed import FeedCache
from .outages import (
    TYPE_INCIDENT,
    Outage,
    Place,
    parse_incidents,
    parse_planned,
    select,
    split_streets,
)
from .texts import texts

_LOGGER = logging.getLogger(__name__)

type DeerConfigEntry = ConfigEntry[DeerCoordinator]


@dataclass
class Match:
    """An outage and the places of it that concern the configured address."""

    outage: Outage
    places: list[Place]

    @property
    def area_only(self) -> bool:
        """Return if only whole-locality or zone lines matched, no named street."""
        return all(place.is_area for place in self.places)

    def as_dict(self) -> dict[str, Any]:
        """Return a compact, JSON friendly description."""
        outage = self.outage
        return {
            "type": outage.kind,
            "id": outage.work_id,
            "start": outage.start.isoformat(),
            "end": outage.end.isoformat(),
            "start_utc": dt_util.as_utc(outage.start).isoformat(),
            "end_utc": dt_util.as_utc(outage.end).isoformat(),
            "end_known": outage.end_known,
            "duration": outage.duration,
            "addresses": [place.text for place in self.places],
            "area_only": self.area_only,
        }


def seen_store(hass: HomeAssistant, entry_id: str) -> Store[dict[str, dict[str, str]]]:
    """Return the storage that remembers outages already announced."""
    return Store(hass, STORAGE_VERSION, f"{DOMAIN}.{entry_id}")


class DeerCoordinator(DataUpdateCoordinator[list[Match]]):
    """Fetch one region every 30 minutes and keep the outages of one address."""

    config_entry: DeerConfigEntry

    def __init__(self, hass: HomeAssistant, entry: DeerConfigEntry, feed: FeedCache) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN} {entry.title}",
            update_interval=SCAN_INTERVAL,
        )
        self._feed = feed
        self.county: str = entry.data[CONF_COUNTY]
        self.region: str = COUNTIES[self.county][0]
        self.locality: str = entry.data[CONF_LOCALITY]
        self.streets: list[str] = split_streets(
            entry.options.get(CONF_STREETS, entry.data.get(CONF_STREETS, ""))
        )
        self._tz = dt_util.get_time_zone(FEED_TIME_ZONE)
        self._store = seen_store(hass, entry.entry_id)
        # Outage key to the date it was last in the feed. None until a baseline exists.
        self._seen: dict[str, str] | None = None
        self._last_good_update: datetime | None = None
        self._degraded = False
        self._unsub_boundary: CALLBACK_TYPE | None = None

    @property
    def has_usable_data(self) -> bool:
        """Return if there is data recent enough to show."""
        return (
            self.data is not None
            and self._last_good_update is not None
            and dt_util.utcnow() - self._last_good_update <= MAX_DATA_AGE
        )

    @property
    def stale(self) -> bool:
        """Return if the shown data is older than the last successful fetch."""
        return not self.last_update_success or self._degraded

    @property
    def seen_count(self) -> int:
        """Return how many outages are remembered as already announced."""
        return len(self._seen or {})

    def _effective_end(self, outage: Outage, now: datetime) -> datetime:
        """Return the end used for state logic.

        An incident without an end time in the feed counts as ongoing until
        the next poll, so it does not turn off between two fetches.
        """
        if outage.kind == TYPE_INCIDENT and not outage.end_known:
            return max(outage.end, now + INCIDENT_ONGOING_EXTENSION)
        return outage.end

    def current(self, now: datetime | None = None) -> list[Match]:
        """Return the matches going on now."""
        now = now or dt_util.now()
        return [
            m for m in self.data or [] if m.outage.start <= now < self._effective_end(m.outage, now)
        ]

    def upcoming(self, now: datetime | None = None) -> list[Match]:
        """Return the matches not over yet, current ones first."""
        now = now or dt_util.now()
        return [m for m in self.data or [] if self._effective_end(m.outage, now) > now]

    async def _async_setup(self) -> None:
        stored = await self._store.async_load()
        if stored is not None:
            self._seen = stored.get("seen", {})

    async def _async_update_data(self) -> list[Match]:
        try:
            feed_result = await self._feed.async_get(self.region)
        except DeerApiError as err:
            if not self.has_usable_data:
                self.async_update_listeners()
            raise UpdateFailed(str(err)) from err

        scheduled, incidents = feed_result.scheduled, feed_result.incidents
        if scheduled is None or incidents is None:
            # One endpoint is down and there is nothing cached for it yet.
            if not self.has_usable_data:
                self.async_update_listeners()
            raise UpdateFailed(f"Feed for {self.region} partially unavailable, no cached data")

        if not feed_result.degraded:
            self._last_good_update = dt_util.utcnow()
        self._degraded = feed_result.degraded

        outages = parse_planned(scheduled, self._tz) + parse_incidents(
            incidents, self._tz, INCIDENT_DEFAULT_DURATION
        )
        matches = [
            Match(outage, places)
            for outage, places in select(outages, self.county, self.locality, self.streets)
        ]
        matches.sort(key=lambda m: (m.outage.start, m.outage.key))
        if not feed_result.degraded:
            await self._async_announce_new(matches)
        self._schedule_boundary(matches)
        return matches

    async def _async_announce_new(self, matches: list[Match]) -> None:
        today = dt_util.now().date().isoformat()
        oldest = (dt_util.now() - timedelta(days=SEEN_RETENTION_DAYS)).date().isoformat()
        previous = self._seen
        seen = {key: day for key, day in (previous or {}).items() if day >= oldest}
        seen.update({m.outage.key: today for m in matches})
        self._seen = seen
        if seen != previous:
            await self._store.async_save({"seen": seen})
        # The first run only records a baseline, so nothing is announced.
        if previous is None:
            return
        for match in matches:
            if match.outage.key not in previous:
                self.hass.bus.async_fire(
                    EVENT_NEW_OUTAGE,
                    {
                        "county": self.county,
                        "locality": self.locality,
                        "streets": self.streets,
                        "message": outage_text(match, self.hass.config.language),
                        **match.as_dict(),
                    },
                )

    @callback
    def _schedule_boundary(self, matches: list[Match]) -> None:
        """Refresh the entities exactly when an outage starts or ends."""
        if self._unsub_boundary:
            self._unsub_boundary()
            self._unsub_boundary = None
        now = dt_util.now()
        times = [
            moment
            for m in matches
            for moment in (m.outage.start, self._effective_end(m.outage, now))
            if moment > now
        ]
        if not times:
            return

        @callback
        def _at_boundary(_: datetime) -> None:
            self._unsub_boundary = None
            self.async_update_listeners()
            self._schedule_boundary(self.data or [])

        self._unsub_boundary = async_track_point_in_utc_time(
            self.hass, _at_boundary, dt_util.as_utc(min(times))
        )

    async def async_shutdown(self) -> None:
        """Cancel the boundary timer."""
        if self._unsub_boundary:
            self._unsub_boundary()
            self._unsub_boundary = None
        await super().async_shutdown()


def outage_text(match: Match, language: str | None) -> str:
    """Return a short description for notifications."""
    text = texts(language)
    outage = match.outage
    start = dt_util.as_local(outage.start)
    end = dt_util.as_local(outage.end)
    day = text["date"]
    when = f"{start.strftime(day)} {start:%H:%M}–{end:%H:%M}"
    if end.date() != start.date():
        when = f"{start.strftime(day)} {start:%H:%M} – {end.strftime(day)} {end:%H:%M}"
    if not outage.end_known:
        when = text["from"].format(start=f"{start.strftime(day)} {start:%H:%M}")
        when = f"{when}, {text['end_unknown']}"
    kind = text["incident"] if outage.kind == TYPE_INCIDENT else text["planned"]
    places = "; ".join(place.text for place in match.places[:5])
    if len(match.places) > 5:
        places += f" (+{len(match.places) - 5})"
    return f"{kind} {when}: {places}"
