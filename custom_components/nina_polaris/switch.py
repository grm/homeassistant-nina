"""Switch platform for NINA Polaris — toggleable equipment states."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import (
    SwitchDeviceClass,
    SwitchEntity,
    SwitchEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api_client import NinaApiClient
from .const import DEFAULT_COOLER_TARGET_TEMP
from .coordinator import NinaCoordinator
from .entity import NinaEntity

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class NinaSwitchDescription(SwitchEntityDescription):
    """Describe a NINA toggle switch."""

    is_on_fn: Callable[[dict], bool | None]
    is_available_fn: Callable[[dict], bool]
    turn_on_fn: Callable[[NinaApiClient, NinaCoordinator], Awaitable[Any]]
    turn_off_fn: Callable[[NinaApiClient, NinaCoordinator], Awaitable[Any]]


# --- Camera cooler ---


def _camera(data: dict) -> dict:
    return ((data or {}).get("equipment") or {}).get("Camera") or {}


def _camera_connected(data: dict) -> bool:
    return bool(_camera(data).get("Connected"))


def _cooler_on(data: dict) -> bool | None:
    cam = _camera(data)
    if not cam.get("Connected"):
        return None
    return bool(cam.get("CoolerOn"))


async def _cooler_turn_on(api: NinaApiClient, coordinator: NinaCoordinator) -> Any:
    target = coordinator.config_entry.options.get("cooler_target_temperature") if coordinator.config_entry else None
    if target is None:
        target = DEFAULT_COOLER_TARGET_TEMP
    return await api.camera_cool(temperature=float(target), minutes=-1)


async def _cooler_turn_off(api: NinaApiClient, coordinator: NinaCoordinator) -> Any:
    return await api.camera_warm(minutes=-1)


# --- Mount tracking ---


def _mount(data: dict) -> dict:
    return ((data or {}).get("equipment") or {}).get("Mount") or {}


def _mount_connected(data: dict) -> bool:
    return bool(_mount(data).get("Connected"))


def _tracking_on(data: dict) -> bool | None:
    m = _mount(data)
    if not m.get("Connected"):
        return None
    return bool(m.get("TrackingEnabled"))


async def _tracking_turn_on(api: NinaApiClient, coordinator: NinaCoordinator) -> Any:
    # 0 = Sidereal (default tracking mode)
    return await api.mount_set_tracking(0)


async def _tracking_turn_off(api: NinaApiClient, coordinator: NinaCoordinator) -> Any:
    # 4 = Stopped
    return await api.mount_set_tracking(4)


SWITCHES: tuple[NinaSwitchDescription, ...] = (
    NinaSwitchDescription(
        key="camera_cooler",
        translation_key="camera_cooler",
        device_class=SwitchDeviceClass.SWITCH,
        icon="mdi:snowflake",
        is_on_fn=_cooler_on,
        is_available_fn=_camera_connected,
        turn_on_fn=_cooler_turn_on,
        turn_off_fn=_cooler_turn_off,
    ),
    NinaSwitchDescription(
        key="mount_tracking",
        translation_key="mount_tracking",
        device_class=SwitchDeviceClass.SWITCH,
        icon="mdi:telescope",
        is_on_fn=_tracking_on,
        is_available_fn=_mount_connected,
        turn_on_fn=_tracking_turn_on,
        turn_off_fn=_tracking_turn_off,
    ),
)


class NinaSwitch(NinaEntity, SwitchEntity):
    """A toggleable NINA equipment state."""

    entity_description: NinaSwitchDescription

    def __init__(self, coordinator: NinaCoordinator, description: NinaSwitchDescription) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{description.key}"

    @property
    def available(self) -> bool:
        if not super().available:
            return False
        return self.entity_description.is_available_fn(self.coordinator.data or {})

    @property
    def is_on(self) -> bool | None:
        return self.entity_description.is_on_fn(self.coordinator.data or {})

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.entity_description.turn_on_fn(self.coordinator.api_client, self.coordinator)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.entity_description.turn_off_fn(self.coordinator.api_client, self.coordinator)
        await self.coordinator.async_request_refresh()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the NINA switch platform."""
    coordinator: NinaCoordinator = entry.runtime_data
    async_add_entities(NinaSwitch(coordinator, desc) for desc in SWITCHES)
