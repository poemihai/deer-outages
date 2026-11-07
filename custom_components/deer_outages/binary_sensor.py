"""Binary sensor telling whether there is an outage at the address right now."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import DeerConfigEntry, outage_text
from .entity import DeerEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DeerConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the binary sensors."""
    coordinator = entry.runtime_data
    async_add_entities([DeerOutageNowSensor(coordinator), DeerAreaOnlySensor(coordinator)])


class DeerAreaOnlySensor(DeerEntity, BinarySensorEntity):
    """On when the current or next outage names only a whole area, not a street.

    Such outages may or may not include the configured address, so this is a
    warning rather than a certain outage.
    """

    _attr_icon = "mdi:map-marker-question"

    def __init__(self, coordinator) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, "area_only")

    @property
    def is_on(self) -> bool:
        """Return if the first upcoming outage covers only an area."""
        upcoming = self.coordinator.upcoming()
        return bool(upcoming and upcoming[0].area_only)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return what the area warning is about."""
        upcoming = self.coordinator.upcoming()
        attributes: dict[str, Any] = {
            "count": len(upcoming),
            **self._common_attributes,
        }
        if upcoming and upcoming[0].area_only:
            first = upcoming[0]
            attributes.update(
                {
                    "addresses": [place.text for place in first.places],
                    "message": outage_text(first, self.hass.config.language),
                }
            )
        return attributes


class DeerOutageNowSensor(DeerEntity, BinarySensorEntity):
    """On while a planned outage or an incident is going on at the address."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_icon = "mdi:flash-alert"

    def __init__(self, coordinator) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, "outage_now")

    @property
    def is_on(self) -> bool:
        """Return if an outage is going on now."""
        return bool(self.coordinator.current())

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the outages going on now."""
        current = self.coordinator.current()
        return {
            "outages": [match.as_dict() for match in current],
            "message": (outage_text(current[0], self.hass.config.language) if current else None),
            **self._common_attributes,
        }
