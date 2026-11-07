"""Small client for the public DEER outage feed."""

from __future__ import annotations

from typing import Any

from aiohttp import ClientError, ClientSession, ClientTimeout
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.loader import async_get_integration

from .const import API_BASE, DOMAIN, REQUEST_TIMEOUT_SECONDS


class DeerApiError(Exception):
    """The feed could not be reached or returned something unusable."""


class DeerApi:
    """Read planned outages and incidents of one DEER region."""

    def __init__(self, session: ClientSession, user_agent: str) -> None:
        """Initialize the client."""
        self._session = session
        self._headers = {"User-Agent": user_agent, "Accept": "application/json"}

    async def _async_get_list(self, path: str) -> list[dict[str, Any]]:
        try:
            async with self._session.get(
                f"{API_BASE}{path}",
                headers=self._headers,
                timeout=ClientTimeout(total=REQUEST_TIMEOUT_SECONDS),
            ) as response:
                response.raise_for_status()
                payload = await response.json(content_type=None)
        except TimeoutError as err:
            raise DeerApiError(f"Timeout while fetching {path}") from err
        except (ClientError, ValueError) as err:
            raise DeerApiError(f"Could not fetch {path}: {err}") from err
        if payload is None:
            return []
        if not isinstance(payload, list) or not all(isinstance(item, dict) for item in payload):
            raise DeerApiError(f"Unexpected response from {path}")
        return payload

    async def async_get_scheduled(self, region: str) -> list[dict[str, Any]]:
        """Return the planned outages of today and the next 15 days."""
        return await self._async_get_list(f"/scheduled/{region}/0/15")

    async def async_get_incidents(self, region: str) -> list[dict[str, Any]]:
        """Return the unplanned outages going on now."""
        return await self._async_get_list(f"/incidents/{region}/0")


async def async_create_api(hass: HomeAssistant) -> DeerApi:
    """Create a client identifying itself with only the integration version."""
    integration = await async_get_integration(hass, DOMAIN)
    return DeerApi(async_get_clientsession(hass), f"ha-deer-outages/{integration.version}")
