"""Tests for the nina_polaris services."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
import voluptuous as vol
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from custom_components.nina_polaris.const import DOMAIN


async def _call(hass: HomeAssistant, service: str, data: dict | None = None) -> None:
    await hass.services.async_call(DOMAIN, service, data or {}, blocking=True)


@pytest.mark.parametrize(
    ("service", "api_method", "kwargs"),
    [
        ("park_mount", "mount_park", {}),
        ("unpark_mount", "mount_unpark", {}),
        ("stop_sequence", "sequence_stop", {}),
        ("start_autofocus", "autofocus_start", {}),
        ("cancel_autofocus", "autofocus_cancel", {}),
        ("plate_solve", "plate_solve", {}),
    ],
)
async def test_simple_services(hass: HomeAssistant, mock_config_entry, service, api_method, kwargs):
    """Each parameterless service routes to the matching api_client method."""
    coordinator = mock_config_entry.runtime_data
    method = AsyncMock()
    setattr(coordinator.api_client, api_method, method)

    await _call(hass, service)
    method.assert_awaited_once_with(**kwargs)


async def test_cool_camera_default_temp(hass: HomeAssistant, mock_config_entry):
    coordinator = mock_config_entry.runtime_data
    coordinator.api_client.camera_cool = AsyncMock()

    await _call(hass, "cool_camera")
    coordinator.api_client.camera_cool.assert_awaited_once_with(temperature=-10.0, minutes=-1.0)


async def test_cool_camera_custom_temp_and_duration(hass: HomeAssistant, mock_config_entry):
    coordinator = mock_config_entry.runtime_data
    coordinator.api_client.camera_cool = AsyncMock()

    await _call(hass, "cool_camera", {"temperature": -15.5, "duration": 12})
    coordinator.api_client.camera_cool.assert_awaited_once_with(temperature=-15.5, minutes=12.0)


async def test_warm_camera(hass: HomeAssistant, mock_config_entry):
    coordinator = mock_config_entry.runtime_data
    coordinator.api_client.camera_warm = AsyncMock()

    await _call(hass, "warm_camera", {"duration": 10})
    coordinator.api_client.camera_warm.assert_awaited_once_with(minutes=10.0)


@pytest.mark.parametrize(
    ("mode", "expected_int"),
    [("sidereal", 0), ("lunar", 1), ("solar", 2), ("king", 3), ("stopped", 4)],
)
async def test_set_tracking_modes(hass: HomeAssistant, mock_config_entry, mode, expected_int):
    coordinator = mock_config_entry.runtime_data
    coordinator.api_client.mount_set_tracking = AsyncMock()

    await _call(hass, "set_tracking", {"mode": mode})
    coordinator.api_client.mount_set_tracking.assert_awaited_once_with(mode=expected_int)


async def test_set_tracking_rejects_unknown_mode(hass: HomeAssistant, mock_config_entry):
    with pytest.raises(vol.Invalid):
        await _call(hass, "set_tracking", {"mode": "warp_drive"})


async def test_start_sequence_default(hass: HomeAssistant, mock_config_entry):
    coordinator = mock_config_entry.runtime_data
    coordinator.api_client.sequence_start = AsyncMock()

    await _call(hass, "start_sequence")
    coordinator.api_client.sequence_start.assert_awaited_once_with(skip_validation=False)


async def test_start_sequence_skip_validation(hass: HomeAssistant, mock_config_entry):
    coordinator = mock_config_entry.runtime_data
    coordinator.api_client.sequence_start = AsyncMock()

    await _call(hass, "start_sequence", {"skip_validation": True})
    coordinator.api_client.sequence_start.assert_awaited_once_with(skip_validation=True)


async def test_api_error_translates_to_ha_error(hass: HomeAssistant, mock_config_entry):
    coordinator = mock_config_entry.runtime_data
    coordinator.api_client.mount_park = AsyncMock(side_effect=RuntimeError("boom"))

    with pytest.raises(HomeAssistantError, match="park_mount failed"):
        await _call(hass, "park_mount")


async def test_service_triggers_refresh(hass: HomeAssistant, mock_config_entry):
    coordinator = mock_config_entry.runtime_data
    coordinator.api_client.mount_park = AsyncMock()
    coordinator.async_request_refresh = AsyncMock()

    await _call(hass, "park_mount")
    coordinator.async_request_refresh.assert_awaited_once()
