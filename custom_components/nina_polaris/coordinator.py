"""DataUpdateCoordinator for NINA."""

import logging
import re
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api_client import NinaApiClient
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN
from .websocket import NinaWebSocket

_LOGGER = logging.getLogger(__name__)


# NINA's RmsText is a string like "Total: 0.42 arcsec, RA: 0.31, Dec: 0.28".
# We surface the leading "Total" value as a numeric sensor.
_RMS_TOTAL_RE = re.compile(r"([0-9]+(?:\.[0-9]+)?)\s*(?:arcsec|\")", re.IGNORECASE)


def _parse_rms_total(rms_text: str | None) -> float | None:
    """Extract the total guiding RMS (arcsec) from NINA's RmsText string."""
    if not rms_text:
        return None
    match = _RMS_TOTAL_RE.search(rms_text)
    if not match:
        return None
    try:
        return float(match.group(1))
    except (TypeError, ValueError):
        return None


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
        self.latest_image_index: int | None = None
        self.latest_image: dict[str, Any] | None = None
        self._latest_image_fetched_index: int | None = None

    async def _refresh_latest_image_metadata(self) -> None:
        """Fetch metadata for the latest image if the index changed."""
        if self.latest_image_index is None:
            return
        if self._latest_image_fetched_index == self.latest_image_index:
            return
        try:
            meta = await self.api_client.get_image_metadata(self.latest_image_index)
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("Could not fetch image metadata: %s", err)
            return
        self.latest_image = meta
        self._latest_image_fetched_index = self.latest_image_index

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from NINA API."""
        try:
            equipment = await self.api_client.get_equipment_info()
            sequence_raw = await self.api_client.get_sequence_state()

            sequence = _parse_sequence_state(sequence_raw)

            # Refresh latest image index (NINA history is 0-indexed; latest = count-1)
            try:
                count = await self.api_client.get_image_history_count()
                if count > 0:
                    self.latest_image_index = count - 1
            except Exception as img_err:  # noqa: BLE001
                _LOGGER.debug("Could not fetch image history count: %s", img_err)

            await self._refresh_latest_image_metadata()

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
                "latest_image": self.latest_image,
            }
        except Exception as err:
            raise UpdateFailed(f"Error communicating with NINA: {err}") from err

    def _on_websocket_event(self, event: dict[str, Any]) -> None:
        """Handle incoming WebSocket events."""
        event_type = event.get("Event", "unknown")
        _LOGGER.debug("WebSocket event received: %s", event_type)

        if event_type == "IMAGE-SAVE":
            if self.latest_image_index is None:
                self.latest_image_index = 0
            else:
                self.latest_image_index += 1
            _LOGGER.debug("New image saved, latest_image_index=%s", self.latest_image_index)

        self.hass.async_create_task(self.async_request_refresh())
