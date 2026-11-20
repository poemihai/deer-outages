"""Sensors for the DEER integration."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .coordinator import DeerConfigEntry, outage_text
from .entity import DeerEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DeerConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the sensors."""
    coordinator = entry.runtime_data
    async_add_entities([DeerNextOutageSensor(coordinator), DeerOutageEndSensor(coordinator)])


class DeerOutageEndSensor(DeerEntity, SensorEntity):
    """When the current (or the next) outage at the address ends."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:clock-end"

    def __init__(self, coordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, "outage_end")

    @property
    def native_value(self) -> datetime | None:
        """Return the end from the active or next outage."""
        now = dt_util.now()
        current = self.coordinator.current(now)
        upcoming = self.coordinator.upcoming(now)
        first = current[0] if current else (upcoming[0] if upcoming else None)
        return first.outage.end if first else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the details of the current or next outage."""
        now = dt_util.now()
        current = self.coordinator.current(now)
        upcoming = self.coordinator.upcoming(now)
        first = current[0] if current else (upcoming[0] if upcoming else None)
        attributes: dict[str, Any] = {
            "count": len(current if current else upcoming),
            **self._common_attributes,
        }
        if first:
            attributes.update(
                {
                    "type": first.outage.kind,
                    "end_known": first.outage.end_known,
                    "addresses": [place.text for place in first.places],
                    "message": outage_text(first, self.hass.config.language),
                }
            )
        return attributes


class DeerNextOutageSensor(DeerEntity, SensorEntity):
    """When the next (or the current) outage at the address starts."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:transmission-tower-off"
    # The list changes often and is of no use in the history database.
    _unrecorded_attributes = frozenset({"outages"})

    def __init__(self, coordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, "next_outage")

    @property
    def native_value(self) -> datetime | None:
        """Return the start of the first future outage."""
        future = self.coordinator.future()
        return future[0].outage.start if future else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the details of the next future outage and the full future list."""
        future = self.coordinator.future()
        attributes: dict[str, Any] = {
            "count": len(future),
            "outages": [match.as_dict() for match in future],
            **self._common_attributes,
        }
        if future:
            first = future[0]
            attributes.update(
                {
                    "end": first.outage.end.isoformat(),
                    "type": first.outage.kind,
                    "addresses": [place.text for place in first.places],
                    "message": outage_text(first, self.hass.config.language),
                }
            )
        return attributes
