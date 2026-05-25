"""NINA Polaris integration for Home Assistant."""

import logging
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .api_client import NinaApiClient
from .const import CONF_PORT, DOMAIN
from .coordinator import NinaCoordinator
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

DASHBOARD_URL_PATH = f"/{DOMAIN}/dashboard/nina-polaris.js"
DASHBOARD_URL = f"{DASHBOARD_URL_PATH}?v=20260525d"


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the dashboard strategy JS early, before any page is served."""
    js_path = Path(__file__).parent / "dashboard" / "nina-polaris.js"
    await hass.http.async_register_static_paths(
        [StaticPathConfig(DASHBOARD_URL_PATH, str(js_path), False)]
    )
    # Register via both mechanisms for maximum compatibility:
    # 1. add_extra_js_url injects into index.html <script> tags
    add_extra_js_url(hass, DASHBOARD_URL)
    # 2. Also register as a Lovelace resource (loaded by load_resource.ts)
    hass.data.setdefault("lovelace_resources", set()).add(DASHBOARD_URL)
    _LOGGER.debug("Registered dashboard strategy JS at %s", DASHBOARD_URL)
    return True


async def _async_register_lovelace_resource(hass: HomeAssistant) -> None:
    """Ensure our JS is registered as a Lovelace resource."""
    try:
        resources = hass.data["lovelace"]["resources"]
        if not resources.loaded:
            await resources.async_load()
            resources.loaded = True
        # Check if already registered
        for item in resources.async_items():
            if DASHBOARD_URL_PATH in item.get("url", ""):
                return
        # Add as a module resource
        await resources.async_create_item({"res_type": "module", "url": DASHBOARD_URL})
        _LOGGER.info("Added dashboard strategy as Lovelace resource")
    except (KeyError, AttributeError, TypeError) as err:
        _LOGGER.debug("Could not register Lovelace resource: %s", err)


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
    await _async_register_lovelace_resource(hass)
    async_setup_services(hass)

    entry.async_on_unload(websocket.async_disconnect)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: NinaConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
