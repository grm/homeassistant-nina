"""NINA Polaris integration for Home Assistant."""

import logging
from contextlib import suppress
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
    if hass.http is not None:
        await hass.http.async_register_static_paths(
            [StaticPathConfig(DASHBOARD_URL_PATH, str(js_path), False)]
        )
    # add_extra_js_url injects into index.html <script> tags.
    with suppress(KeyError, AttributeError):
        add_extra_js_url(hass, DASHBOARD_URL)
    _LOGGER.debug("Registered dashboard strategy JS at %s", DASHBOARD_URL)
    return True


async def _async_register_lovelace_resource(hass: HomeAssistant) -> None:
    """Ensure our JS is registered as a Lovelace resource."""
    lovelace_data = hass.data.get("lovelace")
    if lovelace_data is None:
        _LOGGER.warning(
            "Lovelace not initialized yet — skipping resource registration. "
            "Dashboard strategy will rely on add_extra_js_url injection."
        )
        return

    # Support both legacy dict layout and modern LovelaceData dataclass.
    if isinstance(lovelace_data, dict):
        resources = lovelace_data.get("resources")
    else:
        resources = getattr(lovelace_data, "resources", None)

    if resources is None:
        _LOGGER.warning(
            "Lovelace resources collection not found (mode=%s). "
            "Dashboard strategy will rely on add_extra_js_url injection.",
            type(lovelace_data).__name__,
        )
        return

    # YAML-mode resources collection has no async_create_item.
    if not hasattr(resources, "async_create_item"):
        _LOGGER.warning(
            "Lovelace is in YAML mode — add this to configuration.yaml manually:\n"
            "lovelace:\n  resources:\n    - url: %s\n      type: module",
            DASHBOARD_URL,
        )
        return

    try:
        if not resources.loaded:
            await resources.async_load()
            resources.loaded = True
        for item in resources.async_items():
            if DASHBOARD_URL_PATH in item.get("url", ""):
                _LOGGER.info("Dashboard strategy resource already registered")
                return
        await resources.async_create_item({"res_type": "module", "url": DASHBOARD_URL})
        _LOGGER.warning(
            "Registered NINA Polaris dashboard strategy as Lovelace resource: %s",
            DASHBOARD_URL,
        )
    except Exception:  # noqa: BLE001 — surface the real cause
        _LOGGER.exception("Failed to register dashboard strategy Lovelace resource")


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
