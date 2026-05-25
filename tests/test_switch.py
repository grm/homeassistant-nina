"""Tests for the NINA Polaris switch platform."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.nina_polaris.const import DEFAULT_COOLER_TARGET_TEMP
from custom_components.nina_polaris.switch import SWITCHES, NinaSwitch


@pytest.fixture
def switch_coordinator(mock_nina_api):
    coord = MagicMock()
    coord.api_client = mock_nina_api
    coord.config_entry = MagicMock()
    coord.config_entry.entry_id = "test_entry_switches"
    coord.config_entry.options = {}
    coord.last_update_success = True
    coord.async_request_refresh = AsyncMock()
    coord.data = {
        "equipment": {
            "Camera": {"Connected": True, "CoolerOn": True},
            "Mount": {"Connected": True, "TrackingEnabled": False},
        }
    }
    return coord


def _by_key(key):
    return next(d for d in SWITCHES if d.key == key)


class TestCoolerSwitch:
    def test_state_reflects_cooler_on(self, switch_coordinator):
        sw = NinaSwitch(switch_coordinator, _by_key("camera_cooler"))
        assert sw.is_on is True
        assert sw.available is True

    def test_unavailable_when_camera_disconnected(self, switch_coordinator):
        switch_coordinator.data["equipment"]["Camera"]["Connected"] = False
        sw = NinaSwitch(switch_coordinator, _by_key("camera_cooler"))
        assert sw.available is False
        assert sw.is_on is None

    @pytest.mark.asyncio
    async def test_turn_on_uses_default_target(self, switch_coordinator):
        sw = NinaSwitch(switch_coordinator, _by_key("camera_cooler"))
        await sw.async_turn_on()
        switch_coordinator.api_client.camera_cool.assert_called_once_with(
            temperature=float(DEFAULT_COOLER_TARGET_TEMP), minutes=-1
        )
        switch_coordinator.async_request_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_turn_on_respects_options_override(self, switch_coordinator):
        switch_coordinator.config_entry.options = {"cooler_target_temperature": -15}
        sw = NinaSwitch(switch_coordinator, _by_key("camera_cooler"))
        await sw.async_turn_on()
        switch_coordinator.api_client.camera_cool.assert_called_once_with(temperature=-15.0, minutes=-1)

    @pytest.mark.asyncio
    async def test_turn_off_calls_warm(self, switch_coordinator):
        sw = NinaSwitch(switch_coordinator, _by_key("camera_cooler"))
        await sw.async_turn_off()
        switch_coordinator.api_client.camera_warm.assert_called_once_with(minutes=-1)


class TestTrackingSwitch:
    def test_state_reflects_tracking_enabled(self, switch_coordinator):
        sw = NinaSwitch(switch_coordinator, _by_key("mount_tracking"))
        assert sw.is_on is False

        switch_coordinator.data["equipment"]["Mount"]["TrackingEnabled"] = True
        assert sw.is_on is True

    def test_unavailable_when_mount_disconnected(self, switch_coordinator):
        switch_coordinator.data["equipment"]["Mount"]["Connected"] = False
        sw = NinaSwitch(switch_coordinator, _by_key("mount_tracking"))
        assert sw.available is False

    @pytest.mark.asyncio
    async def test_turn_on_sets_sidereal(self, switch_coordinator):
        sw = NinaSwitch(switch_coordinator, _by_key("mount_tracking"))
        await sw.async_turn_on()
        switch_coordinator.api_client.mount_set_tracking.assert_called_once_with(0)

    @pytest.mark.asyncio
    async def test_turn_off_stops_tracking(self, switch_coordinator):
        sw = NinaSwitch(switch_coordinator, _by_key("mount_tracking"))
        await sw.async_turn_off()
        switch_coordinator.api_client.mount_set_tracking.assert_called_once_with(4)


def test_all_switches_have_unique_keys():
    keys = [d.key for d in SWITCHES]
    assert len(keys) == len(set(keys))
