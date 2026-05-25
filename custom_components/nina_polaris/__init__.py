"""NINA Polaris integration for Home Assistant."""

from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant

from .api_client import NinaApiClient
from .const import CONF_PORT, DOMAIN
from .coordinator import NinaCoordinator
from .websocket import NinaWebSocket

PLATFORMS = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.CAMERA,
    Platform.BUTTON,
    Platform.SWITCH,
]

type NinaConfigEntry = ConfigEntry[NinaCoordinator]

DASHBOARD_URL = f"/{DOMAIN}/dashboard/nina-polaris.js"
DASHBOARD_REGISTERED_KEY = f"{DOMAIN}_dashboard_registered"


async def _async_register_dashboard_strategy(hass: HomeAssistant) -> None:
    """Register the bundled Lovelace strategy JS once.

    Serves the file from the integration directory under a stable URL and
    queues it as an extra frontend module so users can write
    `strategy: type: custom:nina-polaris` without manual resource setup.
    """
    if hass.data.get(DASHBOARD_REGISTERED_KEY):
        return
    js_path = Path(__file__).parent / "dashboard" / "nina-polaris.js"
    await hass.http.async_register_static_paths(
        [StaticPathConfig(DASHBOARD_URL, str(js_path), False)]
    )
    add_extra_js_url(hass, DASHBOARD_URL)
    hass.data[DASHBOARD_REGISTERED_KEY] = True


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
    await _async_register_dashboard_strategy(hass)

    entry.async_on_unload(websocket.async_disconnect)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: NinaConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
