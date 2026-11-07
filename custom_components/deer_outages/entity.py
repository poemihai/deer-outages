"""Shared base of the DEER entities."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import DeerCoordinator


class DeerEntity(CoordinatorEntity[DeerCoordinator]):
    """Base for the entities of one address."""

    _attr_has_entity_name = True
    _attr_attribution = "Data from Distribuție Energie Electrică Romania"

    def __init__(self, coordinator: DeerCoordinator, key: str) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_translation_key = key
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"DEER {entry.title}",
            manufacturer="Distribuție Energie Electrică Romania",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url="https://www.distributie-energie.ro/intreruperi-deer/",
        )

    @property
    def available(self) -> bool:
        """Keep showing the last good data through a short outage of the feed."""
        return self.coordinator.has_usable_data

    @property
    def _common_attributes(self) -> dict[str, Any]:
        return {
            "county": self.coordinator.county,
            "locality": self.coordinator.locality,
            "streets": self.coordinator.streets,
            "stale": self.coordinator.stale,
        }
