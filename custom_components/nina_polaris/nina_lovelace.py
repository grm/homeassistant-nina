"""Auto-registered Lovelace dashboards for NINA Polaris.

For every loaded NINA Polaris config entry we register **one** Lovelace
dashboard with its own sidebar entry. The sidebar title is the instance
name as configured in the integration (e.g. "Trevinca", "TEC140").

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
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.json import json_bytes, json_fragment

from .dashboard_builder import _instance_label, build_dashboard_config

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


class NinaInstanceLovelaceConfig(LovelaceConfig):
    """Lovelace config for a single NINA Polaris instance."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, url_path: str) -> None:
        self._entry_id = entry.entry_id
        super().__init__(
            hass,
            url_path,
            {
                CONF_URL_PATH: url_path,
                CONF_TITLE: entry.title or "NINA",
                CONF_ICON: DEFAULT_ICON,
                CONF_REQUIRE_ADMIN: False,
                CONF_SHOW_IN_SIDEBAR: True,
                "id": f"nina_polaris_{entry.entry_id}",
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
        """Build a fresh single-view dashboard from the registry."""
        return build_dashboard_config(self.hass, entry_id=self._entry_id)

    async def async_json(self, force: bool) -> json_fragment:
        return json_fragment(json_bytes(await self.async_load(force)))


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


@callback
def async_register_instance_dashboard(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Register a per-instance dashboard + sidebar entry for one config entry."""
    dashboards = _get_dashboards_dict(hass)
    if dashboards is None:
        _LOGGER.warning(
            "Lovelace dashboards dict not available — cannot register dashboard for %s",
            entry.title,
        )
        return

    url_path = _url_path_for(entry)

    if url_path in dashboards:
        # Already registered (integration reload).
        _LOGGER.debug("Dashboard %s already registered", url_path)
        return

    # Use the user-configured entry title (config flow title) — that's what
    # users expect to see in the sidebar (e.g. "Trevinca", "TEC140"). Fall
    # back to the device name only if the entry has no title.
    sidebar_title = entry.title or _instance_label(hass, entry.entry_id)

    dashboards[url_path] = NinaInstanceLovelaceConfig(hass, entry, url_path)

    try:
        frontend.async_register_built_in_panel(
            hass,
            component_name=LOVELACE_DOMAIN,
            sidebar_title=sidebar_title,
            sidebar_icon=DEFAULT_ICON,
            frontend_url_path=url_path,
            config={"mode": MODE_STORAGE},
            require_admin=False,
            update=False,
        )
    except ValueError:
        _LOGGER.debug("Frontend panel %s already registered", url_path)
        return

    _LOGGER.info(
        "Registered NINA Polaris dashboard '%s' at /%s (auto-generated)",
        sidebar_title,
        url_path,
    )


@callback
def async_unregister_instance_dashboard(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Tear down a per-instance dashboard when its entry is unloaded."""
    url_path = _url_path_for(entry)

    dashboards = _get_dashboards_dict(hass)
    if dashboards is not None:
        dashboards.pop(url_path, None)

    with suppress(KeyError):
        frontend.async_remove_panel(hass, url_path)
