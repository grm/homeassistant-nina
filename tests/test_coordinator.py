"""Tests for NINA coordinator."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.nina_astro.const import DOMAIN
from custom_components.nina_astro.coordinator import NinaCoordinator, _parse_sequence_state

from .conftest import MOCK_EQUIPMENT_DATA, MOCK_SEQUENCE_PARSED, MOCK_SEQUENCE_RAW


@pytest.fixture
def mock_hass():
    hass = MagicMock(spec=HomeAssistant)
    hass.loop = AsyncMock()
    return hass


@pytest.fixture
def mock_entry():
    entry = MagicMock()
    entry.entry_id = "test_entry_123"
    return entry


@pytest.fixture
def coordinator(mock_hass, mock_entry, mock_nina_api, mock_websocket):
    with patch("custom_components.nina_astro.coordinator.DataUpdateCoordinator.__init__"):
        coord = NinaCoordinator.__new__(NinaCoordinator)
        coord.hass = mock_hass
        coord.config_entry = mock_entry
        coord.api_client = mock_nina_api
        coord.websocket = mock_websocket
        coord.logger = MagicMock()
        coord.name = DOMAIN
        coord.data = None
        coord.async_set_updated_data = MagicMock()
        return coord


class TestParseSequenceState:
    """Test sequence state parsing logic."""

    def test_running_sequence(self):
        result = _parse_sequence_state(MOCK_SEQUENCE_RAW)
        assert result["running"] is True
        assert result["current_target"] == "M42"

    def test_idle_sequence(self):
        idle = [
            {"GlobalTriggers": []},
            {"Status": "FINISHED", "Items": [], "Name": "Start_Container"},
            {"Status": "FINISHED", "Items": [], "Name": "Targets"},
        ]
        result = _parse_sequence_state(idle)
        assert result["running"] is False
        assert result["current_target"] is None

    def test_empty_sequence(self):
        result = _parse_sequence_state([])
        assert result["running"] is False
        assert result["current_target"] is None

    def test_nested_target(self):
        nested = [
            {"GlobalTriggers": []},
            {
                "Status": "RUNNING",
                "Name": "Targets",
                "Items": [
                    {"Status": "FINISHED", "Name": "M31", "Items": []},
                    {
                        "Status": "RUNNING",
                        "Name": "NGC7000",
                        "Items": [],
                    },
                ],
            },
        ]
        result = _parse_sequence_state(nested)
        assert result["running"] is True
        assert result["current_target"] == "NGC7000"


class TestCoordinatorUpdate:
    """Test coordinator data fetching."""

    @pytest.mark.asyncio
    async def test_async_update_data_success(self, coordinator):
        result = await coordinator._async_update_data()

        assert result["equipment"] == MOCK_EQUIPMENT_DATA
        assert result["sequence"] == MOCK_SEQUENCE_PARSED
        coordinator.api_client.get_equipment_info.assert_called_once()
        coordinator.api_client.get_sequence_state.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_update_data_api_error(self, coordinator):
        coordinator.api_client.get_equipment_info = AsyncMock(side_effect=Exception("Connection refused"))

        with pytest.raises(UpdateFailed, match="Error communicating with NINA"):
            await coordinator._async_update_data()

    @pytest.mark.asyncio
    async def test_async_update_data_sequence_error(self, coordinator):
        coordinator.api_client.get_sequence_state = AsyncMock(side_effect=Exception("Timeout"))

        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()


class TestCoordinatorWebSocket:
    """Test coordinator WebSocket handling."""

    def test_websocket_callback_sets_data(self, coordinator):
        coordinator.data = {"equipment": MOCK_EQUIPMENT_DATA, "sequence": MOCK_SEQUENCE_PARSED}
        event = {"Event": "IMAGE-SAVE", "Response": {"FileName": "light_001.fits"}}

        coordinator._on_websocket_event(event)

        coordinator.async_set_updated_data.assert_called_once()
        call_data = coordinator.async_set_updated_data.call_args[0][0]
        assert call_data["last_event"] == event
        assert call_data["equipment"] == MOCK_EQUIPMENT_DATA

    def test_websocket_callback_no_existing_data(self, coordinator):
        coordinator.data = None
        event = {"Event": "CAMERA-CONNECTED", "Response": {}}

        coordinator._on_websocket_event(event)

        coordinator.async_set_updated_data.assert_called_once()
        call_data = coordinator.async_set_updated_data.call_args[0][0]
        assert call_data == {"last_event": event}
