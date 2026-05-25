"""Tests for the NINA Polaris camera platform."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.nina_polaris.camera import NinaLatestImageCamera


@pytest.fixture
def camera_coordinator(mock_nina_api):
    """Build a fake coordinator just sufficient for the camera entity."""
    coord = MagicMock()
    coord.api_client = mock_nina_api
    coord.config_entry = MagicMock()
    coord.config_entry.entry_id = "test_entry_camera"
    coord.latest_image_index = None
    coord.last_update_success = True
    return coord


class TestNinaCamera:
    @pytest.mark.asyncio
    async def test_no_image_returns_none(self, camera_coordinator):
        cam = NinaLatestImageCamera(camera_coordinator)
        assert cam.is_on is False
        assert await cam.async_camera_image() is None
        camera_coordinator.api_client.get_image_bytes.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_image_bytes(self, camera_coordinator):
        camera_coordinator.latest_image_index = 5
        cam = NinaLatestImageCamera(camera_coordinator)
        assert cam.is_on is True

        result = await cam.async_camera_image()
        assert result == b"\xff\xd8\xff\xe0FAKEJPEG"
        camera_coordinator.api_client.get_image_bytes.assert_called_once_with(5, quality=85, resize=False, size=None)

    @pytest.mark.asyncio
    async def test_caches_by_index(self, camera_coordinator):
        camera_coordinator.latest_image_index = 3
        cam = NinaLatestImageCamera(camera_coordinator)

        await cam.async_camera_image()
        await cam.async_camera_image()
        # Same index → second call hits cache, no second fetch.
        assert camera_coordinator.api_client.get_image_bytes.call_count == 1

    @pytest.mark.asyncio
    async def test_refetches_on_new_index(self, camera_coordinator):
        camera_coordinator.latest_image_index = 1
        cam = NinaLatestImageCamera(camera_coordinator)
        await cam.async_camera_image()

        camera_coordinator.latest_image_index = 2
        await cam.async_camera_image()
        assert camera_coordinator.api_client.get_image_bytes.call_count == 2

    @pytest.mark.asyncio
    async def test_passes_resize_when_dimensions_given(self, camera_coordinator):
        camera_coordinator.latest_image_index = 0
        cam = NinaLatestImageCamera(camera_coordinator)

        await cam.async_camera_image(width=800, height=600)
        camera_coordinator.api_client.get_image_bytes.assert_called_once_with(
            0, quality=85, resize=True, size="800x600"
        )

    @pytest.mark.asyncio
    async def test_failed_fetch_does_not_cache(self, camera_coordinator):
        camera_coordinator.latest_image_index = 0
        camera_coordinator.api_client.get_image_bytes = AsyncMock(return_value=None)
        cam = NinaLatestImageCamera(camera_coordinator)

        assert await cam.async_camera_image() is None
        # Restore mock and try again — should refetch (no cache poisoning).
        camera_coordinator.api_client.get_image_bytes = AsyncMock(return_value=b"OK")
        assert await cam.async_camera_image() == b"OK"
