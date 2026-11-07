"""Tests for the entities, the timers and the new outage event."""

from __future__ import annotations

from datetime import datetime

from freezegun.api import FrozenDateTimeFactory
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_capture_events,
    async_fire_time_changed,
)
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
)

from custom_components.deer_outages.const import EVENT_NEW_OUTAGE, SCAN_INTERVAL
from custom_components.deer_outages.diagnostics import (
    async_get_config_entry_diagnostics,
)

from .conftest import INCIDENTS_URL, SCHEDULED_URL, entity_id_by_key, load


def _at(text: str) -> datetime:
    return datetime.fromisoformat(text).replace(tzinfo=dt_util.get_time_zone("Europe/Bucharest"))


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    await hass.config.async_set_time_zone("Europe/Bucharest")
    hass.config.language = "hu"
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_entities(
    hass: HomeAssistant,
    feed: AiohttpClientMocker,
    entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """At noon the street has a planned outage and an incident going on."""
    freezer.move_to(_at("2026-11-06 12:00"))
    await _setup(hass, entry)
    assert entry.state is ConfigEntryState.LOADED

    now_id = entity_id_by_key(hass, entry, "outage_now")
    next_id = entity_id_by_key(hass, entry, "next_outage")
    end_id = entity_id_by_key(hass, entry, "outage_end")
    area_id = entity_id_by_key(hass, entry, "area_only")
    cal_id = entity_id_by_key(hass, entry, "outages")

    state = hass.states.get(now_id)
    assert state.state == "on"
    assert len(state.attributes["outages"]) == 2
    assert state.attributes["message"].startswith("Tervezett áramszünet 11.06. 10:00–14:00")

    state = hass.states.get(next_id)
    assert dt_util.parse_datetime(state.state) == _at("2026-11-06 10:00")
    assert state.attributes["count"] == 3
    assert state.attributes["addresses"] == ["TARGU SECUIESC, Strada GABOR ARON"]

    state = hass.states.get(end_id)
    assert dt_util.parse_datetime(state.state) == _at("2026-11-06 14:00")
    assert state.attributes["end_known"] is True

    # The current outage names a street, so there is no whole-area warning.
    assert hass.states.get(area_id).state == "off"

    result = await hass.services.async_call(
        "calendar",
        "get_events",
        {"start_date_time": "2026-11-06 00:00:00", "end_date_time": "2026-11-20 00:00:00"},
        target={"entity_id": cal_id},
        blocking=True,
        return_response=True,
    )
    events = result[cal_id]["events"]
    assert [e["summary"] for e in events] == [
        "⚡ Áramszünet",
        "⚡ Üzemzavar (vége még nem ismert)",
        "⚡ Áramszünet",
    ]
    assert "teljes település" in events[2]["description"]

    # At 14:00:01 the planned outage is over, but the incident without an end
    # time is still in the feed, so the sensors stay on.
    freezer.move_to(_at("2026-11-06 14:00:01"))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    state = hass.states.get(now_id)
    assert state.state == "on"
    assert [o["id"] for o in state.attributes["outages"]] == ["70001"]
    assert dt_util.parse_datetime(hass.states.get(next_id).state) == _at("2026-11-06 11:30")
    # The assumed end is kept as 2 hours, marked end_known false.
    assert dt_util.parse_datetime(hass.states.get(end_id).state) == _at("2026-11-06 13:30")
    assert hass.states.get(end_id).attributes["end_known"] is False


async def test_new_outage_event(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Only outages that show up after the first fetch are announced."""
    freezer.move_to(_at("2026-11-05 12:00"))
    scheduled = load("scheduled.json")
    aioclient_mock.get(SCHEDULED_URL, json=scheduled[:5])
    aioclient_mock.get(INCIDENTS_URL, json=[])
    events = async_capture_events(hass, EVENT_NEW_OUTAGE)
    await _setup(hass, entry)
    assert events == []

    aioclient_mock.clear_requests()
    aioclient_mock.get(SCHEDULED_URL, json=scheduled)
    aioclient_mock.get(INCIDENTS_URL, json=load("incidents.json"))
    freezer.tick(SCAN_INTERVAL)
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()

    assert sorted(e.data["id"] for e in events) == ["50003", "70001"]
    zone = next(e.data for e in events if e.data["id"] == "50003")
    assert zone["area_only"] is True
    assert zone["message"] == (
        "Tervezett áramszünet 11.12. 08:00–12:00: TARGU SECUIESC, ZONA PT 7 FABRICII"
    )
    assert zone["start_utc"].endswith("+00:00")
    assert zone["end_utc"].endswith("+00:00")


async def test_feed_down(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, entry: MockConfigEntry
) -> None:
    """Setup is retried while the feed cannot be reached."""
    aioclient_mock.get(SCHEDULED_URL, status=500)
    await _setup(hass, entry)
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_no_reannounce_after_reload(
    hass: HomeAssistant,
    feed: AiohttpClientMocker,
    entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Outages announced before a reload are not announced again."""
    freezer.move_to(_at("2026-11-06 12:00"))
    events = async_capture_events(hass, EVENT_NEW_OUTAGE)
    await _setup(hass, entry)
    assert events == []

    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    assert events == []


async def test_stale_after_feed_goes_down(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """The last good data stays with stale: true, then becomes unavailable."""
    aioclient_mock.get(SCHEDULED_URL, json=load("scheduled.json"))
    aioclient_mock.get(INCIDENTS_URL, json=load("incidents.json"))
    freezer.move_to(_at("2026-11-06 12:00"))
    await _setup(hass, entry)
    now_id = entity_id_by_key(hass, entry, "outage_now")
    assert hass.states.get(now_id).state == "on"
    assert hass.states.get(now_id).attributes["stale"] is False

    aioclient_mock.clear_requests()
    aioclient_mock.get(SCHEDULED_URL, status=500)
    aioclient_mock.get(INCIDENTS_URL, status=500)
    freezer.move_to(_at("2026-11-06 12:30"))
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    state = hass.states.get(now_id)
    assert state.state == "on"
    assert state.attributes["stale"] is True

    # Past MAX_DATA_AGE the last good data is no longer shown.
    freezer.move_to(_at("2026-11-06 15:30:01"))
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get(now_id).state == "unavailable"


async def test_boundary_switch(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """The sensors switch exactly when an outage starts, without a poll."""
    aioclient_mock.get(SCHEDULED_URL, json=load("scheduled.json"))
    aioclient_mock.get(INCIDENTS_URL, json=[])
    freezer.move_to(_at("2026-11-12 07:59"))
    await _setup(hass, entry)
    now_id = entity_id_by_key(hass, entry, "outage_now")
    assert hass.states.get(now_id).state == "off"

    freezer.move_to(_at("2026-11-12 08:00"))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get(now_id).state == "on"


async def test_incident_without_end_stays_on(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """An incident without an end time stays on while it is in the feed."""
    aioclient_mock.get(SCHEDULED_URL, json=[])
    aioclient_mock.get(INCIDENTS_URL, json=load("incidents.json"))
    freezer.move_to(_at("2026-11-06 12:00"))
    await _setup(hass, entry)
    now_id = entity_id_by_key(hass, entry, "outage_now")
    assert hass.states.get(now_id).state == "on"

    # Two hours after the start the incident still has no end in the feed.
    freezer.move_to(_at("2026-11-06 14:00:01"))
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get(now_id).state == "on"

    # Once the feed no longer lists it, the sensor turns off.
    aioclient_mock.clear_requests()
    aioclient_mock.get(SCHEDULED_URL, json=[])
    aioclient_mock.get(INCIDENTS_URL, json=[])
    freezer.move_to(_at("2026-11-06 14:45"))
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get(now_id).state == "off"


async def test_diagnostics(
    hass: HomeAssistant,
    feed: AiohttpClientMocker,
    entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Diagnostics expose the coordinator state."""
    freezer.move_to(_at("2026-11-06 12:00"))
    await _setup(hass, entry)
    result = await async_get_config_entry_diagnostics(hass, entry)
    assert result["region"] == "TS"
    assert result["locality"] == "Kézdivásárhely"
    assert result["stale"] is False
    assert result["has_usable_data"] is True
    assert len(result["outages"]) == 3
