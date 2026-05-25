"""NINA Polaris integration for Home Assistant."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant

from .api_client import NinaApiClient
from .const import CONF_PORT
from .coordinator import NinaCoordinator
from .websocket import NinaWebSocket

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.CAMERA, Platform.BUTTON, Platform.SWITCH]

type NinaConfigEntry = ConfigEntry[NinaCoordinator]


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

    entry.async_on_unload(websocket.async_disconnect)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: NinaConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
