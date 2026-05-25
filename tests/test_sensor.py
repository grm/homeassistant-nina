"""Tests for NINA sensor platform."""

from unittest.mock import MagicMock, patch

import pytest

from custom_components.nina_astro.coordinator import NinaCoordinator
from custom_components.nina_astro.sensor import SENSOR_DESCRIPTIONS, NinaSensor, _safe_float

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
def make_sensor(mock_coordinator):
    def _make(key: str):
        description = next(d for d in SENSOR_DESCRIPTIONS if d.key == key)
        with patch.object(NinaSensor, "__init__", lambda self, *a, **kw: None):
            sensor = NinaSensor.__new__(NinaSensor)
            sensor.coordinator = mock_coordinator
            sensor.entity_description = description
            sensor._attr_unique_id = f"test_entry_123_{key}"
        return sensor

    return _make


class TestSafeFloat:
    """Test the _safe_float helper."""

    def test_normal_float(self):
        assert _safe_float(19.75) == 19.75

    def test_integer(self):
        assert _safe_float(35) == 35

    def test_nan_string(self):
        assert _safe_float("NaN") is None

    def test_nan_float(self):
        assert _safe_float(float("nan")) is None

    def test_inf(self):
        assert _safe_float(float("inf")) is None

    def test_none(self):
        assert _safe_float(None) is None

    def test_numeric_string(self):
        assert _safe_float("3.14") == 3.14

    def test_non_numeric_string(self):
        assert _safe_float("hello") is None

    def test_rounds_to_two_decimals(self):
        assert _safe_float(3.14159) == 3.14


class TestSensorValues:
    """Test sensor value extraction from real NINA data."""

    def test_camera_temperature(self, make_sensor):
        sensor = make_sensor("camera_temperature")
        assert sensor.native_value == -10.0

    def test_camera_cooler_power(self, make_sensor):
        sensor = make_sensor("camera_cooler_power")
        assert sensor.native_value == 80

    def test_guider_ra_distance(self, make_sensor):
        sensor = make_sensor("guider_ra_distance")
        assert sensor.native_value == 0.11

    def test_guider_dec_distance(self, make_sensor):
        sensor = make_sensor("guider_dec_distance")
        assert sensor.native_value == 1.11

    def test_focuser_position(self, make_sensor):
        sensor = make_sensor("focuser_position")
        assert sensor.native_value == 12500

    def test_focuser_temperature(self, make_sensor):
        sensor = make_sensor("focuser_temperature")
        assert sensor.native_value == 5.0

    def test_mount_ra(self, make_sensor):
        sensor = make_sensor("mount_ra")
        assert sensor.native_value == 5.58

    def test_mount_dec(self, make_sensor):
        sensor = make_sensor("mount_dec")
        assert sensor.native_value == 22.0

    def test_mount_altitude(self, make_sensor):
        sensor = make_sensor("mount_altitude")
        assert sensor.native_value == 45.0

    def test_mount_azimuth(self, make_sensor):
        sensor = make_sensor("mount_azimuth")
        assert sensor.native_value == 180.0

    def test_mount_time_to_flip(self, make_sensor):
        sensor = make_sensor("mount_time_to_flip")
        assert sensor.native_value == 120.5

    def test_sequence_target(self, make_sensor):
        sensor = make_sensor("sequence_target")
        assert sensor.native_value == "M42"

    def test_weather_temperature(self, make_sensor):
        sensor = make_sensor("weather_temperature")
        assert sensor.native_value == 19.75

    def test_weather_humidity(self, make_sensor):
        sensor = make_sensor("weather_humidity")
        assert sensor.native_value == 35

    def test_weather_pressure(self, make_sensor):
        sensor = make_sensor("weather_pressure")
        assert sensor.native_value == 882.05

    def test_weather_dewpoint(self, make_sensor):
        sensor = make_sensor("weather_dewpoint")
        assert sensor.native_value == 3.86

    def test_weather_wind_speed(self, make_sensor):
        sensor = make_sensor("weather_wind_speed")
        assert sensor.native_value == 5

    def test_weather_sky_quality(self, make_sensor):
        sensor = make_sensor("weather_sky_quality")
        assert sensor.native_value == 20.47

    def test_weather_sky_temperature(self, make_sensor):
        sensor = make_sensor("weather_sky_temperature")
        assert sensor.native_value == -7.76


class TestSensorNaNHandling:
    """Test sensors handle NaN values from disconnected equipment."""

    def test_nan_altitude(self, make_sensor, mock_coordinator):
        mock_coordinator.data["equipment"]["Mount"]["Altitude"] = "NaN"
        sensor = make_sensor("mount_altitude")
        assert sensor.native_value is None

    def test_nan_focuser_temp(self, make_sensor, mock_coordinator):
        mock_coordinator.data["equipment"]["Focuser"]["Temperature"] = "NaN"
        sensor = make_sensor("focuser_temperature")
        assert sensor.native_value is None

    def test_nan_float_value(self, make_sensor, mock_coordinator):
        mock_coordinator.data["equipment"]["Mount"]["Azimuth"] = float("nan")
        sensor = make_sensor("mount_azimuth")
        assert sensor.native_value is None


class TestSensorNoData:
    """Test sensors when no data is available."""

    def test_returns_none_when_no_data(self, make_sensor, mock_coordinator):
        mock_coordinator.data = None
        sensor = make_sensor("camera_temperature")
        assert sensor.native_value is None

    def test_returns_none_when_no_equipment(self, make_sensor, mock_coordinator):
        mock_coordinator.data = {"sequence": MOCK_SEQUENCE_PARSED}
        sensor = make_sensor("camera_temperature")
        assert sensor.native_value is None


class TestSensorDescriptions:
    """Test sensor entity descriptions."""

    def test_all_descriptions_have_unique_keys(self):
        keys = [d.key for d in SENSOR_DESCRIPTIONS]
        assert len(keys) == len(set(keys))

    def test_all_descriptions_have_translation_key(self):
        for desc in SENSOR_DESCRIPTIONS:
            assert desc.translation_key is not None

    def test_unique_id_format(self, make_sensor):
        sensor = make_sensor("camera_temperature")
        assert sensor._attr_unique_id == "test_entry_123_camera_temperature"
