"""Fixtures for NINA integration tests."""

from unittest.mock import AsyncMock, MagicMock

import pytest

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
