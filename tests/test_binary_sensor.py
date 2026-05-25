"""Tests for NINA binary sensor platform."""

from unittest.mock import MagicMock, patch

import pytest

from custom_components.nina_astro.binary_sensor import (
    BINARY_SENSOR_DESCRIPTIONS,
    NinaBinarySensor,
)
from custom_components.nina_astro.coordinator import NinaCoordinator

from .conftest import MOCK_EQUIPMENT_DATA, MOCK_SEQUENCE_PARSED


@pytest.fixture
def mock_coordinator():
    import copy

    coord = MagicMock(spec=NinaCoordinator)
    coord.config_entry = MagicMock()
    coord.config_entry.entry_id = "test_entry_123"
    coord.data = {"equipment": copy.deepcopy(MOCK_EQUIPMENT_DATA), "sequence": {**MOCK_SEQUENCE_PARSED}}
    return coord


@pytest.fixture
def make_binary_sensor(mock_coordinator):
    def _make(key: str):
        description = next(d for d in BINARY_SENSOR_DESCRIPTIONS if d.key == key)
        with patch.object(NinaBinarySensor, "__init__", lambda self, *a, **kw: None):
            sensor = NinaBinarySensor.__new__(NinaBinarySensor)
            sensor.coordinator = mock_coordinator
            sensor.entity_description = description
            sensor._attr_unique_id = f"test_entry_123_{key}"
        return sensor

    return _make


class TestBinarySensorConnected:
    """Test equipment connection binary sensors."""

    def test_camera_connected(self, make_binary_sensor):
        sensor = make_binary_sensor("camera_connected")
        assert sensor.is_on is True

    def test_mount_connected(self, make_binary_sensor):
        sensor = make_binary_sensor("mount_connected")
        assert sensor.is_on is True

    def test_guider_connected(self, make_binary_sensor):
        sensor = make_binary_sensor("guider_connected")
        assert sensor.is_on is True

    def test_focuser_connected(self, make_binary_sensor):
        sensor = make_binary_sensor("focuser_connected")
        assert sensor.is_on is True

    def test_filterwheel_connected(self, make_binary_sensor):
        sensor = make_binary_sensor("filterwheel_connected")
        assert sensor.is_on is True

    def test_dome_disconnected(self, make_binary_sensor):
        sensor = make_binary_sensor("dome_connected")
        assert sensor.is_on is False

    def test_rotator_disconnected(self, make_binary_sensor):
        sensor = make_binary_sensor("rotator_connected")
        assert sensor.is_on is False

    def test_weather_connected(self, make_binary_sensor):
        sensor = make_binary_sensor("weather_connected")
        assert sensor.is_on is True

    def test_safety_monitor_connected(self, make_binary_sensor):
        sensor = make_binary_sensor("safety_monitor_connected")
        assert sensor.is_on is True


class TestBinarySensorState:
    """Test state binary sensors."""

    def test_sequence_running(self, make_binary_sensor):
        sensor = make_binary_sensor("sequence_running")
        assert sensor.is_on is True

    def test_sequence_not_running(self, make_binary_sensor, mock_coordinator):
        mock_coordinator.data["sequence"]["running"] = False
        sensor = make_binary_sensor("sequence_running")
        assert sensor.is_on is False

    def test_mount_tracking(self, make_binary_sensor):
        sensor = make_binary_sensor("mount_tracking")
        assert sensor.is_on is True

    def test_mount_not_tracking(self, make_binary_sensor, mock_coordinator):
        mock_coordinator.data["equipment"]["Mount"]["TrackingEnabled"] = False
        sensor = make_binary_sensor("mount_tracking")
        assert sensor.is_on is False

    def test_mount_slewing(self, make_binary_sensor):
        sensor = make_binary_sensor("mount_slewing")
        assert sensor.is_on is False

    def test_mount_at_park(self, make_binary_sensor):
        sensor = make_binary_sensor("mount_at_park")
        assert sensor.is_on is False

    def test_camera_exposing(self, make_binary_sensor):
        sensor = make_binary_sensor("camera_exposing")
        assert sensor.is_on is True

    def test_camera_cooler_on(self, make_binary_sensor):
        sensor = make_binary_sensor("camera_cooler_on")
        assert sensor.is_on is True

    def test_safety_is_safe(self, make_binary_sensor):
        sensor = make_binary_sensor("safety_is_safe")
        assert sensor.is_on is False

    def test_safety_is_safe_true(self, make_binary_sensor, mock_coordinator):
        mock_coordinator.data["equipment"]["SafetyMonitor"]["IsSafe"] = True
        sensor = make_binary_sensor("safety_is_safe")
        assert sensor.is_on is True


class TestBinarySensorNoData:
    """Test binary sensors when no data is available."""

    def test_returns_none_when_no_data(self, make_binary_sensor, mock_coordinator):
        mock_coordinator.data = None
        sensor = make_binary_sensor("camera_connected")
        assert sensor.is_on is None

    def test_returns_none_when_no_equipment(self, make_binary_sensor, mock_coordinator):
        mock_coordinator.data = {"sequence": MOCK_SEQUENCE_PARSED}
        sensor = make_binary_sensor("camera_connected")
        assert sensor.is_on is None


class TestBinarySensorDescriptions:
    """Test binary sensor entity descriptions."""

    def test_all_descriptions_have_unique_keys(self):
        keys = [d.key for d in BINARY_SENSOR_DESCRIPTIONS]
        assert len(keys) == len(set(keys))

    def test_all_descriptions_have_translation_key(self):
        for desc in BINARY_SENSOR_DESCRIPTIONS:
            assert desc.translation_key is not None

    def test_unique_id_format(self, make_binary_sensor):
        sensor = make_binary_sensor("camera_connected")
        assert sensor._attr_unique_id == "test_entry_123_camera_connected"
