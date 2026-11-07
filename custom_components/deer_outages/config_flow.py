"""Config and options flows for the DEER integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
)

from .api import DeerApiError, async_create_api
from .const import CONF_COUNTY, CONF_LOCALITY, CONF_STREETS, COUNTIES, DOMAIN
from .coordinator import DeerConfigEntry
from .outages import normalize, normalize_locality, split_streets

DEFAULT_COUNTY = "Covasna"
DEFAULT_LOCALITY = "Târgu Secuiesc"


def _unique_id(county: str, locality: str, streets: list[str]) -> str:
    """Return the unique id of one address, the same for RO and HU spelling."""
    return "|".join(
        [
            normalize(county),
            normalize_locality(locality),
            *sorted(normalize(s) for s in streets),
        ]
    )


def _county_selector() -> SelectSelector:
    ordered = sorted(COUNTIES.items(), key=lambda item: item[1][1])
    return SelectSelector(
        SelectSelectorConfig(
            options=[SelectOptionDict(value=key, label=display) for key, (_, display) in ordered],
            mode=SelectSelectorMode.DROPDOWN,
        )
    )


def _streets_selector() -> TextSelector:
    return TextSelector(TextSelectorConfig(multiline=True))


def _title(locality: str, streets: list[str]) -> str:
    return f"{locality} – {', '.join(streets)}" if streets else locality


class DeerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Ask for the county, the locality and optionally streets."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: DeerConfigEntry) -> DeerOptionsFlow:
        """Return the options flow."""
        return DeerOptionsFlow()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Pick the address."""
        errors: dict[str, str] = {}
        if user_input is not None:
            county = user_input[CONF_COUNTY]
            locality = user_input[CONF_LOCALITY].strip()
            streets = split_streets(user_input.get(CONF_STREETS))
            if not normalize(locality):
                errors[CONF_LOCALITY] = "locality_required"
            else:
                await self.async_set_unique_id(_unique_id(county, locality, streets))
                self._abort_if_unique_id_configured()
                api = await async_create_api(self.hass)
                try:
                    await api.async_get_scheduled(COUNTIES[county][0])
                except DeerApiError:
                    errors["base"] = "cannot_connect"
                else:
                    return self.async_create_entry(
                        title=_title(locality, streets),
                        data={CONF_COUNTY: county, CONF_LOCALITY: locality},
                        options={CONF_STREETS: ", ".join(streets)},
                    )

        defaults = user_input or {}
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_COUNTY, default=defaults.get(CONF_COUNTY, DEFAULT_COUNTY)
                ): _county_selector(),
                vol.Required(
                    CONF_LOCALITY,
                    default=defaults.get(CONF_LOCALITY, DEFAULT_LOCALITY),
                ): str,
                vol.Optional(
                    CONF_STREETS, default=defaults.get(CONF_STREETS, "")
                ): _streets_selector(),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change the county, locality or streets of an existing address."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            county = user_input[CONF_COUNTY]
            locality = user_input[CONF_LOCALITY].strip()
            streets = split_streets(user_input.get(CONF_STREETS))
            if not normalize(locality):
                errors[CONF_LOCALITY] = "locality_required"
            else:
                unique_id = _unique_id(county, locality, streets)
                if any(
                    other.entry_id != entry.entry_id and other.unique_id == unique_id
                    for other in self._async_current_entries()
                ):
                    errors["base"] = "already_configured"
                else:
                    api = await async_create_api(self.hass)
                    try:
                        await api.async_get_scheduled(COUNTIES[county][0])
                    except DeerApiError:
                        errors["base"] = "cannot_connect"
                    else:
                        return self.async_update_reload_and_abort(
                            entry,
                            unique_id=unique_id,
                            title=_title(locality, streets),
                            data={CONF_COUNTY: county, CONF_LOCALITY: locality},
                            options={CONF_STREETS: ", ".join(streets)},
                        )

        defaults = user_input or {
            CONF_COUNTY: entry.data[CONF_COUNTY],
            CONF_LOCALITY: entry.data[CONF_LOCALITY],
            CONF_STREETS: entry.options.get(CONF_STREETS, ""),
        }
        schema = vol.Schema(
            {
                vol.Required(CONF_COUNTY, default=defaults[CONF_COUNTY]): _county_selector(),
                vol.Required(CONF_LOCALITY, default=defaults[CONF_LOCALITY]): str,
                vol.Optional(
                    CONF_STREETS, default=defaults.get(CONF_STREETS, "")
                ): _streets_selector(),
            }
        )
        return self.async_show_form(step_id="reconfigure", data_schema=schema, errors=errors)


class DeerOptionsFlow(OptionsFlowWithReload):
    """Change the streets."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Show the current streets."""
        if user_input is not None:
            streets = split_streets(user_input.get(CONF_STREETS))
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                title=_title(self.config_entry.data[CONF_LOCALITY], streets),
            )
            return self.async_create_entry(data={CONF_STREETS: ", ".join(streets)})

        current = self.config_entry.options.get(CONF_STREETS, "")
        schema = vol.Schema({vol.Optional(CONF_STREETS, default=current): _streets_selector()})
        return self.async_show_form(step_id="init", data_schema=schema)
