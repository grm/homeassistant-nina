"""DataUpdateCoordinator for NINA."""

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api_client import NinaApiClient
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN
from .websocket import NinaWebSocket

_LOGGER = logging.getLogger(__name__)


def _parse_sequence_state(sequence_raw: list[dict[str, Any]]) -> dict[str, Any]:
    """Parse the sequence state array into a usable dict."""
    running = False
    current_target = None

    for item in sequence_raw:
        status = item.get("Status")
        if status == "RUNNING":
            running = True
            name = item.get("Name")
            if name and name != "Start_Container":
                current_target = name
            for sub in item.get("Items", []):
                if sub.get("Status") == "RUNNING":
                    sub_name = sub.get("Name")
                    if sub_name:
                        current_target = sub_name

    return {
        "running": running,
        "current_target": current_target,
    }


class NinaCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to manage fetching NINA data."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        api_client: NinaApiClient,
        websocket: NinaWebSocket,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=config_entry,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.api_client = api_client
        self.websocket = websocket
        self.websocket.set_callback(self._on_websocket_event)

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from NINA API."""
        try:
            equipment = await self.api_client.get_equipment_info()
            sequence_raw = await self.api_client.get_sequence_state()

            sequence = _parse_sequence_state(sequence_raw)

            _LOGGER.debug(
                "NINA update: camera_connected=%s, mount_connected=%s, "
                "guider_connected=%s, sequence_running=%s, target=%s",
                equipment.get("Camera", {}).get("Connected"),
                equipment.get("Mount", {}).get("Connected"),
                equipment.get("Guider", {}).get("Connected"),
                sequence.get("running"),
                sequence.get("current_target"),
            )

            return {
                "equipment": equipment,
                "sequence": sequence,
            }
        except Exception as err:
            raise UpdateFailed(f"Error communicating with NINA: {err}") from err

    def _on_websocket_event(self, event: dict[str, Any]) -> None:
        """Handle incoming WebSocket events."""
        event_type = event.get("Event", "unknown")
        _LOGGER.debug("WebSocket event received: %s", event_type)
        self.async_set_updated_data({**self.data, "last_event": event} if self.data else {"last_event": event})
