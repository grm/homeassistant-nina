"""Auto-registered Lovelace dashboard for NINA Polaris.

One sidebar entry ("NINA") covers every loaded config entry. With a single
instance the dashboard opens straight on that telescope. With several, the
first view is a menu of telescopes stacked one under the other, and each
telescope is a subview.

The dashboard config is rebuilt on every page load from the entity
registry — same pattern as the built-in Energy / Map dashboards, except
we use a `LovelaceConfig` subclass so HA itself drives the regeneration.
"""

from __future__ import annotations

import logging
import re
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
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.json import json_bytes, json_fragment

from .const import DOMAIN
from .dashboard_builder import DASHBOARD_URL_PATH, build_dashboard_config

_LOGGER = logging.getLogger(__name__)

DEFAULT_ICON = "mdi:telescope"
URL_PREFIX = "nina-"


def _slugify(value: str) -> str:
    """Lowercase + only [a-z0-9-]. Used to build a URL path from the title."""
    s = value.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    return s or "instance"


def _url_path_for(entry: ConfigEntry) -> str:
    """Stable, human-readable URL path for one entry.

    Format: `nina-<slug>-<entry_id_short>`. The short entry_id suffix
    guarantees uniqueness even if two NINA instances share a title, while
    keeping the URL readable.
    """
    label = entry.title or "instance"
    return f"{URL_PREFIX}{_slugify(label)}-{entry.entry_id[:8]}"


class NinaLovelaceConfig(LovelaceConfig):
    """Lovelace config covering every loaded NINA Polaris instance."""

    def __init__(self, hass: HomeAssistant, url_path: str) -> None:
        super().__init__(
            hass,
            url_path,
            {
                CONF_URL_PATH: url_path,
                CONF_TITLE: "NINA",
                CONF_ICON: DEFAULT_ICON,
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
        config = await self.async_load(False)
        return {"mode": "generated", "views": len(config.get("views", []))}

    async def async_load(self, force: bool) -> dict[str, Any]:
        """Build a fresh dashboard from the registry (one view, or a menu)."""
        return build_dashboard_config(self.hass)

    async def async_json(self, force: bool) -> json_fragment:
        return json_fragment(json_bytes(await self.async_load(force)))


# Kept so reloads of older installs can still be type-checked by name.
NinaInstanceLovelaceConfig = NinaLovelaceConfig


# --------------------------------------------------------------------------- #
# Lovelace internal plumbing                                                  #
# --------------------------------------------------------------------------- #


def _get_dashboards_dict(hass: HomeAssistant) -> dict[str, Any] | None:
    lovelace_data = hass.data.get(LOVELACE_DOMAIN)
    if lovelace_data is None:
        return None
    if isinstance(lovelace_data, dict):
        return lovelace_data.get("dashboards")
    return getattr(lovelace_data, "dashboards", None)


def _drop_panel(hass: HomeAssistant, url_path: str) -> None:
    dashboards = _get_dashboards_dict(hass)
    if dashboards is not None:
        dashboards.pop(url_path, None)
    with suppress(KeyError):
        frontend.async_remove_panel(hass, url_path)


@callback
def async_register_instance_dashboard(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Ensure the shared NINA dashboard exists and drop this entry's old panel.

    Releases before 0.8 registered one sidebar item per config entry
    (`nina-<slug>-<id>`). Those panels are removed here so a reload collapses
    them into the single NINA menu.
    """
    _drop_panel(hass, _url_path_for(entry))

    dashboards = _get_dashboards_dict(hass)
    if dashboards is None:
        _LOGGER.warning(
            "Lovelace dashboards dict not available — cannot register dashboard for %s",
            entry.title,
        )
        return

    if DASHBOARD_URL_PATH in dashboards:
        _LOGGER.debug("Dashboard %s already registered", DASHBOARD_URL_PATH)
        return

    dashboards[DASHBOARD_URL_PATH] = NinaLovelaceConfig(hass, DASHBOARD_URL_PATH)

    try:
        frontend.async_register_built_in_panel(
            hass,
            component_name=LOVELACE_DOMAIN,
            sidebar_title="NINA",
            sidebar_icon=DEFAULT_ICON,
            frontend_url_path=DASHBOARD_URL_PATH,
            config={"mode": MODE_STORAGE},
            require_admin=False,
            update=False,
        )
    except ValueError:
        _LOGGER.debug("Frontend panel %s already registered", DASHBOARD_URL_PATH)
        return

    _LOGGER.info("Registered NINA Polaris dashboard at /%s (auto-generated)", DASHBOARD_URL_PATH)


@callback
def async_unregister_instance_dashboard(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Drop a legacy per-entry panel, and the shared dashboard when none remain."""
    _drop_panel(hass, _url_path_for(entry))

    others = [
        other
        for other in hass.config_entries.async_entries(DOMAIN)
        if other.entry_id != entry.entry_id and other.state is ConfigEntryState.LOADED
    ]
    if others:
        return

    _drop_panel(hass, DASHBOARD_URL_PATH)
