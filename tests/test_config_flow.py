"""Tests for the config and options flows."""

from __future__ import annotations

from homeassistant.config_entries import SOURCE_RECONFIGURE, SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
)

from custom_components.deer_outages.const import DOMAIN

from .conftest import SCHEDULED_URL

USER_INPUT = {
    "county": "Covasna",
    "locality": "Kézdivásárhely",
    "streets": "Gábor Áron, Ady Endre",
}


async def test_user_flow(hass: HomeAssistant, feed: AiohttpClientMocker) -> None:
    """The address is stored with the streets as an option."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Kézdivásárhely – Gábor Áron, Ady Endre"
    assert result["data"] == {"county": "Covasna", "locality": "Kézdivásárhely"}
    assert result["options"] == {"streets": "Gábor Áron, Ady Endre"}
    assert result["result"].unique_id == "COVASNA|TARGU SECUIESC|ADY ENDRE|GABOR ARON"

    # The same address in Romanian is a duplicate.
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {**USER_INPUT, "locality": "Târgu Secuiesc", "streets": "ady endre, GABOR ARON"},
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_user_flow_cannot_connect(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """A feed error is shown on the form."""
    aioclient_mock.get(SCHEDULED_URL, status=503)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_options_flow(
    hass: HomeAssistant, feed: AiohttpClientMocker, entry: MockConfigEntry
) -> None:
    """Changing the streets updates the title."""
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"streets": "Kossuth Lajos"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == {"streets": "Kossuth Lajos"}
    assert entry.title == "Kézdivásárhely – Kossuth Lajos"


async def test_reconfigure_flow(
    hass: HomeAssistant, feed: AiohttpClientMocker, entry: MockConfigEntry
) -> None:
    """The whole address can be changed and the entry is reloaded."""
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_RECONFIGURE, "entry_id": entry.entry_id}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"county": "Sibiu", "locality": "Sibiu", "streets": "Calea Dumbrăvii"},
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    await hass.async_block_till_done()
    assert entry.data == {"county": "Sibiu", "locality": "Sibiu"}
    assert entry.options == {"streets": "Calea Dumbrăvii"}
    assert entry.title == "Sibiu – Calea Dumbrăvii"
    assert entry.unique_id == "SIBIU|SIBIU|CALEA DUMBRAVII"


async def test_reconfigure_duplicate(
    hass: HomeAssistant, feed: AiohttpClientMocker, entry: MockConfigEntry
) -> None:
    """Reconfiguring to an address that already exists is refused."""
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # A second entry follows the whole locality of Târgu Secuiesc.
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"county": "Covasna", "locality": "Târgu Secuiesc", "streets": ""}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_RECONFIGURE, "entry_id": entry.entry_id}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"county": "Covasna", "locality": "Târgu Secuiesc", "streets": ""}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "already_configured"}
