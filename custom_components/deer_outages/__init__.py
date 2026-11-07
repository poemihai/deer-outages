"""DEER power outages: planned outages and incidents at your address."""

from __future__ import annotations

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import DeerConfigEntry, DeerCoordinator, seen_store
from .feed import FeedCache

PLATFORMS = [Platform.BINARY_SENSOR, Platform.CALENDAR, Platform.SENSOR]


def _feed_cache(hass: HomeAssistant) -> FeedCache:
    """Return the feed cache shared by every config entry."""
    registry = hass.data.setdefault(DOMAIN, {})
    cache = registry.get("feed")
    if cache is None:
        cache = registry["feed"] = FeedCache(hass)
    return cache


async def async_setup_entry(hass: HomeAssistant, entry: DeerConfigEntry) -> bool:
    """Set up one address from a config entry."""
    coordinator = DeerCoordinator(hass, entry, _feed_cache(hass))
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: DeerConfigEntry) -> bool:
    """Unload a config entry and stop its boundary timer."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if coordinator := entry.runtime_data:
        await coordinator.async_shutdown()
    return unloaded


async def async_remove_entry(hass: HomeAssistant, entry: DeerConfigEntry) -> None:
    """Forget the announced outages when the address is removed."""
    await seen_store(hass, entry.entry_id).async_remove()
