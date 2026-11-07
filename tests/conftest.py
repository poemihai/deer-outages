"""Shared fixtures for the DEER tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
)

from custom_components.deer_outages.const import (
    API_BASE,
    CONF_COUNTY,
    CONF_LOCALITY,
    CONF_STREETS,
    DOMAIN,
)

FIXTURES = Path(__file__).parent / "fixtures"
SCHEDULED_URL = f"{API_BASE}/scheduled/TS/0/15"
INCIDENTS_URL = f"{API_BASE}/incidents/TS/0"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Let Home Assistant load the integration from custom_components."""


def load(name: str) -> list[dict[str, Any]]:
    """Return a fixture file."""
    return json.loads((FIXTURES / name).read_text("utf-8"))


@pytest.fixture
def feed(aioclient_mock: AiohttpClientMocker) -> AiohttpClientMocker:
    """Serve the fixtures as the DEER feed."""
    aioclient_mock.get(SCHEDULED_URL, json=load("scheduled.json"))
    aioclient_mock.get(INCIDENTS_URL, json=load("incidents.json"))
    return aioclient_mock


@pytest.fixture
def entry() -> MockConfigEntry:
    """Return an entry for one street in Târgu Secuiesc."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Kézdivásárhely – Gábor Áron",
        unique_id="COVASNA|TARGU SECUIESC|GABOR ARON",
        data={CONF_COUNTY: "Covasna", CONF_LOCALITY: "Kézdivásárhely"},
        options={CONF_STREETS: "Gábor Áron"},
    )


def entity_id_by_key(hass: HomeAssistant, entry: MockConfigEntry, key: str) -> str:
    """Return the entity id of the entry's entity with the given key."""
    wanted = f"{entry.entry_id}_{key}"
    for entity_id, entity in er.async_get(hass).entities.items():
        if entity.unique_id == wanted:
            return entity_id
    raise AssertionError(f"No entity with unique id {wanted}")
