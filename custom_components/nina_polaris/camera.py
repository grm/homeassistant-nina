"""Camera platform for NINA Polaris — exposes the latest captured image."""

from __future__ import annotations

import logging

from homeassistant.components.camera import Camera
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import NinaCoordinator
from .entity import NinaEntity

_LOGGER = logging.getLogger(__name__)


class NinaLatestImageCamera(NinaEntity, Camera):
    """Camera entity exposing the latest image captured by NINA.

    The image bytes are proxied through Home Assistant — the browser only
    talks to HA, never directly to the NINA host. This means the dashboard
    keeps working from outside the local network (e.g. via Nabu Casa).
    """

    _attr_translation_key = "latest_image"
    _attr_brand = "NINA"
    _attr_frame_interval = 2.0  # we refresh on websocket IMAGE-SAVE anyway

    def __init__(self, coordinator: NinaCoordinator) -> None:
        """Initialize the camera entity."""
        NinaEntity.__init__(self, coordinator)
        Camera.__init__(self)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_latest_image"
        self._cached_index: int | None = None
        self._cached_bytes: bytes | None = None

    @property
    def is_on(self) -> bool:
        """Camera is 'on' as soon as we have at least one image."""
        return self.coordinator.latest_image_index is not None

    async def async_camera_image(self, width: int | None = None, height: int | None = None) -> bytes | None:
        """Return bytes of the latest image, fetching from NINA on change."""
        index = self.coordinator.latest_image_index
        if index is None:
            return None

        # Cache by index so we don't hammer NINA on every Lovelace refresh.
        if index == self._cached_index and self._cached_bytes is not None:
            return self._cached_bytes

        # If the dashboard requests a specific render size, ask NINA to resize.
        size = None
        resize = False
        if width and height:
            size = f"{width}x{height}"
            resize = True

        image = await self.coordinator.api_client.get_image_bytes(index, quality=85, resize=resize, size=size)
        if image is not None:
            self._cached_index = index
            self._cached_bytes = image
        return image


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the NINA camera platform."""
    coordinator: NinaCoordinator = entry.runtime_data
    async_add_entities([NinaLatestImageCamera(coordinator)])
