"""Shared cache of the DEER feed, one fetch per region and polling interval.

Every config entry in the same county polls the same region feed, so the
fetch is done once and shared. The two endpoints are fetched in parallel
and kept separately, so a failing endpoint does not lose the other one.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .api import DeerApi, DeerApiError, async_create_api
from .const import SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)
_RETRIES = 2


class FeedResult:
    """The two feed lists and whether any of them had to fall back to cache."""

    __slots__ = ("degraded", "incidents", "scheduled")

    def __init__(
        self,
        scheduled: list[dict[str, Any]] | None,
        incidents: list[dict[str, Any]] | None,
        degraded: bool,
    ) -> None:
        """Initialize the result."""
        self.scheduled = scheduled
        self.incidents = incidents
        self.degraded = degraded


class FeedCache:
    """Fetch each region once per SCAN_INTERVAL, shared by all its entries."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the cache."""
        self._hass = hass
        self._lock = asyncio.Lock()
        self._data: dict[
            str, tuple[list[dict[str, Any]], list[dict[str, Any]], datetime, bool]
        ] = {}

    async def async_get(self, region: str) -> FeedResult:
        """Return the feed of a region, reusing a fresh fetch if available.

        A list that could not be fetched falls back to the last good one and
        the result is marked degraded. Raises DeerApiError when nothing at all
        is usable.
        """
        async with self._lock:
            cached = self._data.get(region)
            if cached is not None and dt_util.utcnow() - cached[2] < SCAN_INTERVAL:
                return FeedResult(cached[0], cached[1], cached[3])

            api = await async_create_api(self._hass)
            scheduled, incidents = await asyncio.gather(
                self._async_fetch(api, region, "scheduled"),
                self._async_fetch(api, region, "incidents"),
            )

            old_scheduled, old_incidents = cached[:2] if cached else (None, None)
            scheduled = scheduled if scheduled is not None else old_scheduled
            incidents = incidents if incidents is not None else old_incidents

            if scheduled is None and incidents is None:
                raise DeerApiError(f"Region {region}: both endpoints failed and nothing is cached")

            degraded = scheduled is old_scheduled or incidents is old_incidents
            self._data[region] = (scheduled, incidents, dt_util.utcnow(), degraded)
            return FeedResult(scheduled, incidents, degraded)

    async def _async_fetch(
        self, api: DeerApi, region: str, kind: str
    ) -> list[dict[str, Any]] | None:
        """Fetch one endpoint, retrying once on failure."""
        fetch = api.async_get_scheduled if kind == "scheduled" else api.async_get_incidents
        last_error: DeerApiError | None = None
        for _ in range(_RETRIES):
            try:
                return await fetch(region)
            except DeerApiError as err:
                last_error = err
        _LOGGER.debug(
            "DEER %s fetch failed for %s after %s attempts: %s",
            kind,
            region,
            _RETRIES,
            last_error,
        )
        return None
