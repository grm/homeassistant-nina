"""Fixtures for NINA integration tests."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading of custom_components in every test."""
    yield


MOCK_EQUIPMENT_DATA = {
    "Camera": {
        "Connected": True,
        "Temperature": -10.0,
        "CoolerPower": 80,
        "CoolerOn": True,
        "IsExposing": True,
        "CameraState": "Exposing",
    },
    "Mount": {
        "Connected": True,
        "TrackingEnabled": True,
        "Slewing": False,
        "AtPark": False,
        "RightAscension": 5.583,
        "Declination": 22.0,
        "Altitude": 45.0,
        "Azimuth": 180.0,
        "TimeToMeridianFlip": 120.5,
        "SideOfPier": "pierEast",
    },
    "Guider": {
        "Connected": True,
        "LastGuideStep": {
            "RADistanceRaw": 0.112,
            "DECDistanceRaw": 1.112,
            "RADuration": 0,
            "DECDuration": -210,
        },
    },
    "Focuser": {"Connected": True, "Position": 12500, "Temperature": 5.0},
    "FilterWheel": {"Connected": True, "IsMoving": False},
    "Dome": {"Connected": False},
    "Rotator": {"Connected": False},
    "SafetyMonitor": {"Connected": True, "IsSafe": False},
    "WeatherData": {
        "Connected": True,
        "Temperature": 19.75,
        "Humidity": 35,
        "Pressure": 882.05,
        "DewPoint": 3.86,
        "WindSpeed": 5,
        "SkyQuality": 20.47,
        "SkyTemperature": -7.76,
        "RainRate": 10,
    },
}

MOCK_SEQUENCE_RAW = [
    {"GlobalTriggers": []},
    {"Iterations": 0, "Status": "FINISHED", "Items": [], "Name": "Start_Container"},
    {
        "Iterations": 0,
        "Status": "RUNNING",
        "Items": [
            {
                "Iterations": 1,
                "Status": "RUNNING",
                "Name": "M42",
                "Items": [],
            }
        ],
        "Name": "Targets",
    },
]

MOCK_SEQUENCE_PARSED = {
    "running": True,
    "current_target": "M42",
}


@pytest.fixture
def mock_nina_api():
    """Create a mock NINA API client."""
    client = AsyncMock()
    client.get_version = AsyncMock(return_value="2.2.15.1")
    client.get_nina_version = AsyncMock(return_value="3.2.0.9001")
    client.get_equipment_info = AsyncMock(return_value=MOCK_EQUIPMENT_DATA)
    client.get_sequence_state = AsyncMock(return_value=MOCK_SEQUENCE_RAW)
    client.get_image_history_count = AsyncMock(return_value=0)
    client.get_image_bytes = AsyncMock(return_value=b"\xff\xd8\xff\xe0FAKEJPEG")
    client.mount_park = AsyncMock(return_value="Parking")
    client.mount_unpark = AsyncMock(return_value="Unparking")
    client.mount_set_tracking = AsyncMock(return_value="OK")
    client.sequence_start = AsyncMock(return_value="Started")
    client.sequence_stop = AsyncMock(return_value="Stopped")
    client.autofocus_start = AsyncMock(return_value="OK")
    client.autofocus_cancel = AsyncMock(return_value="OK")
    client.plate_solve = AsyncMock(return_value={"Success": True})
    client.camera_cool = AsyncMock(return_value="OK")
    client.camera_warm = AsyncMock(return_value="OK")
    client.close = AsyncMock()
    return client


@pytest.fixture
def mock_websocket():
    """Create a mock NINA WebSocket client."""
    ws = MagicMock()
    ws.async_connect = AsyncMock()
    ws.async_disconnect = AsyncMock()
    ws.set_callback = MagicMock()
    return ws


@pytest.fixture
async def mock_config_entry(hass, mock_nina_api, mock_websocket):
    """Set up a fully loaded NINA Polaris config entry with mocked deps.

    Tests can read coordinator + api via `entry.runtime_data` and
    `entry.runtime_data.api`.
    """
    from custom_components.nina_polaris.const import CONF_PORT, DOMAIN

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"host": "192.0.2.10", CONF_PORT: 1888},
        title="NINA Polaris",
        unique_id="test-nina",
    )
    entry.add_to_hass(hass)

    with (
        _patch("custom_components.nina_polaris.NinaApiClient", return_value=mock_nina_api),
        _patch("custom_components.nina_polaris.NinaWebSocket", return_value=mock_websocket),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    return entry


def _patch(target, **kwargs):
    from unittest.mock import patch

    return patch(target, **kwargs)
