"""Auto-registered Lovelace dashboard for NINA Polaris.

Subclasses `LovelaceConfig` so HA itself asks us for the dashboard config
every time a user opens it. No service call, no storage, no JS — the
dashboard is rebuilt on-the-fly from the entity registry on every load.

This is the same pattern used by `homeassistant.components.energy` and
the built-in Map dashboard, except we generate the cards dynamically.
"""

from __future__ import annotations

import logging
from contextlib import suppress
from typing import Any

from homeassistant.components import frontend
from homeassistant.components.lovelace import DOMAIN as LOVELACE_DOMAIN
from homeassistant.components.lovelace.const import (
    CONF_ICON,
    CONF_REQUIRE_ADMIN,
    CONF_SHOW_IN_SIDEBAR,
    CONF_TITLE,
    CONF_URL_PATH,
    MODE_STORAGE,
)
from homeassistant.components.lovelace.dashboard import LovelaceConfig
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.json import json_bytes, json_fragment

from .dashboard_builder import build_dashboard_config

_LOGGER = logging.getLogger(__name__)

NINA_DASHBOARD_URL_PATH = "nina-polaris"
NINA_DASHBOARD_TITLE = "NINA Polaris"
NINA_DASHBOARD_ICON = "mdi:telescope"


class NinaLovelaceConfig(LovelaceConfig):
    """Lovelace config that rebuilds itself from the entity registry."""

    def __init__(self, hass: HomeAssistant) -> None:
        super().__init__(
            hass,
            NINA_DASHBOARD_URL_PATH,
            {
                CONF_URL_PATH: NINA_DASHBOARD_URL_PATH,
                CONF_TITLE: NINA_DASHBOARD_TITLE,
                CONF_ICON: NINA_DASHBOARD_ICON,
                CONF_REQUIRE_ADMIN: False,
                CONF_SHOW_IN_SIDEBAR: True,
                "id": "nina_polaris",
                "mode": MODE_STORAGE,
            },
        )

    @property
    def mode(self) -> str:
        return MODE_STORAGE

    async def async_get_info(self) -> dict[str, Any]:
        # Lovelace asks for this when listing dashboards. Return the size
        # of the latest config so the UI shows non-empty.
        config = await self.async_load(False)
        return {
            "mode": "generated",
            "views": len(config.get("views", [])),
        }

    async def async_load(self, force: bool) -> dict[str, Any]:
        """Build the dashboard fresh from the registry every call."""
        return build_dashboard_config(self.hass)

    async def async_json(self, force: bool) -> json_fragment:
        """Return JSON-serialized config (called by the WS API).

        We rebuild every time and never cache — the registry is the source
        of truth, and a Lovelace config is small enough that re-encoding is
        cheap compared to a stale dashboard.
        """
        return json_fragment(json_bytes(await self.async_load(force)))

    # async_save / async_delete are inherited (raise HomeAssistantError) —
    # this dashboard is not user-editable through the UI Raw Config Editor.
    # That's intentional: any edit would be wiped on next load anyway.


@callback
def async_register_dashboard(hass: HomeAssistant) -> None:
    """Register our auto-generated dashboard with Lovelace + frontend."""
    lovelace_data = hass.data.get(LOVELACE_DOMAIN)
    if lovelace_data is None:
        _LOGGER.warning("Lovelace not initialized yet — NINA Polaris dashboard cannot register")
        return

    # `lovelace_data` is a dict in HA <2024.10, a LovelaceData dataclass after.
    if isinstance(lovelace_data, dict):
        dashboards = lovelace_data.get("dashboards")
    else:
        dashboards = getattr(lovelace_data, "dashboards", None)
    if dashboards is None:
        _LOGGER.warning("Lovelace dashboards dict not available — cannot register NINA dashboard")
        return

    if NINA_DASHBOARD_URL_PATH in dashboards:
        # Already registered (could happen on integration reload).
        _LOGGER.debug("NINA Polaris dashboard already registered")
        return

    dashboards[NINA_DASHBOARD_URL_PATH] = NinaLovelaceConfig(hass)

    try:
        frontend.async_register_built_in_panel(
            hass,
            component_name=LOVELACE_DOMAIN,
            sidebar_title=NINA_DASHBOARD_TITLE,
            sidebar_icon=NINA_DASHBOARD_ICON,
            frontend_url_path=NINA_DASHBOARD_URL_PATH,
            config={"mode": MODE_STORAGE},
            require_admin=False,
            update=False,
        )
    except ValueError:
        # Panel already registered (integration reload).
        _LOGGER.debug("NINA Polaris frontend panel already registered")
        return

    _LOGGER.info(
        "Registered NINA Polaris dashboard at /%s (auto-generated, rebuilt on every load)",
        NINA_DASHBOARD_URL_PATH,
    )


@callback
def async_unregister_dashboard(hass: HomeAssistant) -> None:
    """Tear down the dashboard when the integration unloads."""
    lovelace_data = hass.data.get(LOVELACE_DOMAIN)
    if lovelace_data is not None:
        dashboards = (
            lovelace_data.get("dashboards")
            if isinstance(lovelace_data, dict)
            else getattr(lovelace_data, "dashboards", None)
        )
        if dashboards is not None:
            dashboards.pop(NINA_DASHBOARD_URL_PATH, None)

    with suppress(KeyError):
        frontend.async_remove_panel(hass, NINA_DASHBOARD_URL_PATH)
