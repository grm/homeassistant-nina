"""Tests for the NINA Polaris button platform."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.nina_polaris.button import BUTTONS, NinaButton


@pytest.fixture
def button_coordinator(mock_nina_api):
    coord = MagicMock()
    coord.api_client = mock_nina_api
    coord.config_entry = MagicMock()
    coord.config_entry.entry_id = "test_entry_buttons"
    coord.last_update_success = True
    coord.async_request_refresh = AsyncMock()
    coord.data = {
        "equipment": {
            "Mount": {"Connected": True},
            "Camera": {"Connected": True},
            "Focuser": {"Connected": True},
        },
        "sequence": {"running": False, "current_target": None},
    }
    return coord


def _by_key(key: str):
    return next(d for d in BUTTONS if d.key == key)


class TestButtonAvailability:
    def test_park_unavailable_when_mount_disconnected(self, button_coordinator):
        button_coordinator.data["equipment"]["Mount"]["Connected"] = False
        btn = NinaButton(button_coordinator, _by_key("mount_park"))
        assert btn.available is False

    def test_park_available_when_mount_connected(self, button_coordinator):
        btn = NinaButton(button_coordinator, _by_key("mount_park"))
        assert btn.available is True

    def test_sequence_start_only_when_idle(self, button_coordinator):
        btn = NinaButton(button_coordinator, _by_key("sequence_start"))
        assert btn.available is True
        button_coordinator.data["sequence"]["running"] = True
        assert btn.available is False

    def test_sequence_stop_only_when_running(self, button_coordinator):
        btn = NinaButton(button_coordinator, _by_key("sequence_stop"))
        assert btn.available is False
        button_coordinator.data["sequence"]["running"] = True
        assert btn.available is True

    def test_unavailable_when_no_data(self, button_coordinator):
        button_coordinator.data = None
        btn = NinaButton(button_coordinator, _by_key("autofocus_start"))
        assert btn.available is False


class TestButtonPress:
    @pytest.mark.asyncio
    async def test_park_calls_api(self, button_coordinator):
        btn = NinaButton(button_coordinator, _by_key("mount_park"))
        await btn.async_press()
        button_coordinator.api_client.mount_park.assert_called_once()
        button_coordinator.async_request_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_unpark_calls_api(self, button_coordinator):
        btn = NinaButton(button_coordinator, _by_key("mount_unpark"))
        await btn.async_press()
        button_coordinator.api_client.mount_unpark.assert_called_once()

    @pytest.mark.asyncio
    async def test_sequence_start(self, button_coordinator):
        btn = NinaButton(button_coordinator, _by_key("sequence_start"))
        await btn.async_press()
        button_coordinator.api_client.sequence_start.assert_called_once()

    @pytest.mark.asyncio
    async def test_sequence_stop(self, button_coordinator):
        btn = NinaButton(button_coordinator, _by_key("sequence_stop"))
        await btn.async_press()
        button_coordinator.api_client.sequence_stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_autofocus(self, button_coordinator):
        btn = NinaButton(button_coordinator, _by_key("autofocus_start"))
        await btn.async_press()
        button_coordinator.api_client.autofocus_start.assert_called_once()

    @pytest.mark.asyncio
    async def test_plate_solve(self, button_coordinator):
        btn = NinaButton(button_coordinator, _by_key("plate_solve"))
        await btn.async_press()
        button_coordinator.api_client.plate_solve.assert_called_once()

    @pytest.mark.asyncio
    async def test_press_propagates_errors(self, button_coordinator):
        button_coordinator.api_client.mount_park = AsyncMock(side_effect=RuntimeError("boom"))
        btn = NinaButton(button_coordinator, _by_key("mount_park"))
        with pytest.raises(RuntimeError, match="boom"):
            await btn.async_press()


def test_all_buttons_have_unique_keys():
    keys = [d.key for d in BUTTONS]
    assert len(keys) == len(set(keys))
