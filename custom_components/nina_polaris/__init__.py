"""NINA Polaris integration for Home Assistant."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .api_client import NinaApiClient
from .const import CONF_PORT, DOMAIN
from .coordinator import NinaCoordinator
from .nina_lovelace import async_register_dashboard, async_unregister_dashboard
from .services import async_setup_services
from .websocket import NinaWebSocket

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.CAMERA,
    Platform.BUTTON,
    Platform.SWITCH,
]

type NinaConfigEntry = ConfigEntry[NinaCoordinator]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the integration (no-op — kept for compatibility)."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: NinaConfigEntry) -> bool:
    """Set up NINA from a config entry."""
    host = entry.data[CONF_HOST]
    port = entry.data[CONF_PORT]

    api_client = NinaApiClient(host, port)
    websocket = NinaWebSocket(hass, host, port)
    coordinator = NinaCoordinator(hass, entry, api_client, websocket)

    await coordinator.async_config_entry_first_refresh()
    await websocket.async_connect()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    async_setup_services(hass)

    # Register/refresh the auto-generated NINA Polaris dashboard. Tracked once
    # per HA process via a sentinel so multiple config entries don't try to
    # register the same panel twice.
    domain_state = hass.data.setdefault(DOMAIN, {})
    if not domain_state.get("dashboard_registered"):
        try:
            async_register_dashboard(hass)
            domain_state["dashboard_registered"] = True
        except Exception:  # noqa: BLE001 — never block entry setup on a UI-only feature
            _LOGGER.exception(
                "Failed to register the NINA Polaris auto-dashboard. "
                "The integration is otherwise fully functional; entities "
                "and services are still available."
            )

    entry.async_on_unload(websocket.async_disconnect)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: NinaConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    # If this was the last NINA entry, drop the dashboard panel too.
    remaining = [e for e in hass.config_entries.async_entries(DOMAIN) if e.entry_id != entry.entry_id]
    if not remaining:
        async_unregister_dashboard(hass)
        hass.data.get(DOMAIN, {}).pop("dashboard_registered", None)
    return unloaded
