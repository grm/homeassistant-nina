"""Config flow for NINA Polaris."""

import logging
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_HOST
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
)

from .const import (
    API_BASE_PATH,
    CONF_MONITORING_CAMERA_ENTITY,
    CONF_PORT,
    DEFAULT_PORT,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class NinaConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for NINA."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow for this entry."""
        return NinaOptionsFlow()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            port = user_input[CONF_PORT]

            try:
                await self._test_connection(host, port)
            except (aiohttp.ClientError, TimeoutError):
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(f"nina_{host}_{port}")
                self._abort_if_unique_id_configured()
                # Use the active NINA profile name as the entry title — this
                # is the human-readable name the user picked in NINA itself
                # (e.g. "Trevinca", "TEC140"). Fall back to host:port so the
                # flow never blocks on the optional profile lookup.
                title = await self._get_profile_name(host, port) or f"NINA ({host}:{port})"
                return self.async_create_entry(title=title, data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default="localhost"): str,
                    vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
                }
            ),
            errors=errors,
        )

    async def _test_connection(self, host: str, port: int) -> None:
        """Test if we can connect to the NINA API."""
        url = f"http://{host}:{port}{API_BASE_PATH}/version"
        async with (
            aiohttp.ClientSession() as session,
            session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp,
        ):
            resp.raise_for_status()

    async def _get_profile_name(self, host: str, port: int) -> str | None:
        """Fetch the active NINA profile name. Returns None on any failure."""
        url = f"http://{host}:{port}{API_BASE_PATH}/profile/show?active=true"
        try:
            async with (
                aiohttp.ClientSession() as session,
                session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp,
            ):
                resp.raise_for_status()
                payload = await resp.json()
        except (aiohttp.ClientError, TimeoutError, ValueError) as exc:
            _LOGGER.debug("Could not fetch active profile name: %s", exc)
            return None
        # Response shape: {"Response": {"Name": "...", ...}, "Success": true, ...}
        response = payload.get("Response") if isinstance(payload, dict) else None
        if isinstance(response, dict):
            name = response.get("Name")
            if isinstance(name, str) and name.strip():
                return name.strip()
        return None


class NinaOptionsFlow(OptionsFlow):
    """Handle the options flow for NINA Polaris.

    Currently lets the user pick a monitoring camera entity (e.g. an RTSP rig
    cam set up via the Generic Camera integration) that will be embedded in
    the auto-generated dashboard. Selecting "no camera" removes the tile.
    """

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            # An empty selector value clears the option entirely.
            cleaned = {k: v for k, v in user_input.items() if v not in (None, "", [])}
            return self.async_create_entry(title="", data=cleaned)

        current = self.config_entry.options.get(CONF_MONITORING_CAMERA_ENTITY, "")
        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_MONITORING_CAMERA_ENTITY,
                    description={"suggested_value": current},
                ): EntitySelector(EntitySelectorConfig(domain="camera")),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
