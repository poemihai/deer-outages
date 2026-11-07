"""Diagnostics support for the DEER integration."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

from .coordinator import DeerConfigEntry


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: DeerConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for one configured address."""
    coordinator = entry.runtime_data
    return {
        "entry": entry.as_dict(),
        "region": coordinator.region,
        "county": coordinator.county,
        "locality": coordinator.locality,
        "streets": coordinator.streets,
        "last_update_success": coordinator.last_update_success,
        "stale": coordinator.stale,
        "has_usable_data": coordinator.has_usable_data,
        "seen_count": coordinator.seen_count,
        "outages": [match.as_dict() for match in coordinator.data or []],
    }
