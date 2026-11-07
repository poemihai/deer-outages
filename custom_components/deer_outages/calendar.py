"""Calendar of the outages at the address."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import DeerConfigEntry, Match
from .entity import DeerEntity
from .outages import TYPE_INCIDENT
from .texts import texts


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DeerConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the calendar."""
    async_add_entities([DeerOutageCalendar(entry.runtime_data)])


def match_event(match: Match, language: str | None) -> CalendarEvent:
    """Build the calendar event of one outage."""
    text = texts(language)
    outage = match.outage
    summary = text["calendar_incident" if outage.kind == TYPE_INCIDENT else "calendar_planned"]
    if not outage.end_known:
        summary += f" ({text['end_unknown']})"
    lines = [place.text for place in match.places]
    if match.area_only:
        lines.append(text["area"])
    if outage.duration:
        lines.append(text["duration"].format(duration=outage.duration))
    return CalendarEvent(
        start=outage.start,
        end=outage.end,
        summary=summary,
        description="\n".join(lines),
        uid=outage.key,
    )


class DeerOutageCalendar(DeerEntity, CalendarEntity):
    """Planned outages and incidents at the address as events."""

    _attr_icon = "mdi:calendar-alert"

    def __init__(self, coordinator) -> None:
        """Initialize the calendar."""
        super().__init__(coordinator, "outages")

    @property
    def event(self) -> CalendarEvent | None:
        """Return the outage going on now or the next one."""
        upcoming = self.coordinator.upcoming()
        return match_event(upcoming[0], self.hass.config.language) if upcoming else None

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        """Return the outages that overlap the requested range."""
        return [
            match_event(match, hass.config.language)
            for match in self.coordinator.data or []
            if match.outage.start < end_date and match.outage.end > start_date
        ]
