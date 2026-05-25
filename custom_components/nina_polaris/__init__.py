"""NINA Polaris integration for Home Assistant."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .api_client import NinaApiClient
from .const import CONF_PORT
from .coordinator import NinaCoordinator
from .nina_lovelace import (
    async_register_instance_dashboard,
    async_unregister_instance_dashboard,
)
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

    # Register a per-instance dashboard with its own sidebar entry.
    # Wrapped so a Lovelace API change can never block the integration.
    try:
        async_register_instance_dashboard(hass, entry)
    except Exception:  # noqa: BLE001
        _LOGGER.exception(
            "Failed to register the NINA Polaris dashboard for '%s'. "
            "The integration is otherwise fully functional; entities "
            "and services are still available.",
            entry.title,
        )

    entry.async_on_unload(websocket.async_disconnect)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))

    return True


async def _async_options_updated(hass: HomeAssistant, entry: NinaConfigEntry) -> None:
    """Reload the entry when options change so the dashboard picks up changes."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: NinaConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    # Drop this entry's sidebar dashboard.
    try:
        async_unregister_instance_dashboard(hass, entry)
    except Exception:  # noqa: BLE001
        _LOGGER.exception("Failed to unregister NINA Polaris dashboard for '%s'", entry.title)
    return unloaded
