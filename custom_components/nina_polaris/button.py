"""Button platform for NINA Polaris — exposes one-shot actions."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api_client import NinaApiClient
from .coordinator import NinaCoordinator
from .entity import NinaEntity

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class NinaButtonDescription(ButtonEntityDescription):
    """Describe a NINA action button."""

    action: Callable[[NinaApiClient], Awaitable[object]]
    available_when: Callable[[dict], bool] | None = None


def _equipment_connected(domain: str) -> Callable[[dict], bool]:
    def _check(data: dict) -> bool:
        equipment = (data or {}).get("equipment") or {}
        return bool((equipment.get(domain) or {}).get("Connected"))

    return _check


def _equipment_disconnected(domain: str) -> Callable[[dict], bool]:
    """Available when the device exists in NINA's equipment list but is offline."""

    def _check(data: dict) -> bool:
        equipment = (data or {}).get("equipment") or {}
        device = equipment.get(domain)
        # Only show "connect" when NINA has reported the device at least once.
        return device is not None and not device.get("Connected", False)

    return _check


def _sequence_running(data: dict) -> bool:
    return bool(((data or {}).get("sequence") or {}).get("running"))


def _sequence_idle(data: dict) -> bool:
    return not _sequence_running(data)


BUTTONS: tuple[NinaButtonDescription, ...] = (
    # --- Camera --- #
    NinaButtonDescription(
        key="camera_connect",
        translation_key="camera_connect",
        icon="mdi:lan-connect",
        action=lambda api: api.device_connect("camera"),
        available_when=_equipment_disconnected("Camera"),
    ),
    NinaButtonDescription(
        key="camera_disconnect",
        translation_key="camera_disconnect",
        icon="mdi:lan-disconnect",
        action=lambda api: api.device_disconnect("camera"),
        available_when=_equipment_connected("Camera"),
    ),
    NinaButtonDescription(
        key="camera_abort_exposure",
        translation_key="camera_abort_exposure",
        icon="mdi:camera-off-outline",
        action=lambda api: api.camera_abort_exposure(),
        available_when=_equipment_connected("Camera"),
    ),
    # --- Mount --- #
    NinaButtonDescription(
        key="mount_connect",
        translation_key="mount_connect",
        icon="mdi:lan-connect",
        action=lambda api: api.device_connect("mount"),
        available_when=_equipment_disconnected("Mount"),
    ),
    NinaButtonDescription(
        key="mount_disconnect",
        translation_key="mount_disconnect",
        icon="mdi:lan-disconnect",
        action=lambda api: api.device_disconnect("mount"),
        available_when=_equipment_connected("Mount"),
    ),
    NinaButtonDescription(
        key="mount_park",
        translation_key="mount_park",
        icon="mdi:parking",
        action=lambda api: api.mount_park(),
        available_when=_equipment_connected("Mount"),
    ),
    NinaButtonDescription(
        key="mount_unpark",
        translation_key="mount_unpark",
        icon="mdi:telescope",
        action=lambda api: api.mount_unpark(),
        available_when=_equipment_connected("Mount"),
    ),
    # --- Focuser --- #
    NinaButtonDescription(
        key="focuser_connect",
        translation_key="focuser_connect",
        icon="mdi:lan-connect",
        action=lambda api: api.device_connect("focuser"),
        available_when=_equipment_disconnected("Focuser"),
    ),
    NinaButtonDescription(
        key="focuser_disconnect",
        translation_key="focuser_disconnect",
        icon="mdi:lan-disconnect",
        action=lambda api: api.device_disconnect("focuser"),
        available_when=_equipment_connected("Focuser"),
    ),
    NinaButtonDescription(
        key="autofocus_start",
        translation_key="autofocus_start",
        icon="mdi:image-filter-center-focus",
        action=lambda api: api.autofocus_start(),
        available_when=_equipment_connected("Focuser"),
    ),
    # --- Guider --- #
    NinaButtonDescription(
        key="guider_connect",
        translation_key="guider_connect",
        icon="mdi:lan-connect",
        action=lambda api: api.device_connect("guider"),
        available_when=_equipment_disconnected("Guider"),
    ),
    NinaButtonDescription(
        key="guider_disconnect",
        translation_key="guider_disconnect",
        icon="mdi:lan-disconnect",
        action=lambda api: api.device_disconnect("guider"),
        available_when=_equipment_connected("Guider"),
    ),
    NinaButtonDescription(
        key="guider_start",
        translation_key="guider_start",
        icon="mdi:crosshairs",
        action=lambda api: api.guider_start(),
        available_when=_equipment_connected("Guider"),
    ),
    NinaButtonDescription(
        key="guider_stop",
        translation_key="guider_stop",
        icon="mdi:crosshairs-off",
        action=lambda api: api.guider_stop(),
        available_when=_equipment_connected("Guider"),
    ),
    # --- Filter wheel --- #
    NinaButtonDescription(
        key="filterwheel_connect",
        translation_key="filterwheel_connect",
        icon="mdi:lan-connect",
        action=lambda api: api.device_connect("filterwheel"),
        available_when=_equipment_disconnected("FilterWheel"),
    ),
    NinaButtonDescription(
        key="filterwheel_disconnect",
        translation_key="filterwheel_disconnect",
        icon="mdi:lan-disconnect",
        action=lambda api: api.device_disconnect("filterwheel"),
        available_when=_equipment_connected("FilterWheel"),
    ),
    # --- Dome --- #
    NinaButtonDescription(
        key="dome_connect",
        translation_key="dome_connect",
        icon="mdi:lan-connect",
        action=lambda api: api.device_connect("dome"),
        available_when=_equipment_disconnected("Dome"),
    ),
    NinaButtonDescription(
        key="dome_disconnect",
        translation_key="dome_disconnect",
        icon="mdi:lan-disconnect",
        action=lambda api: api.device_disconnect("dome"),
        available_when=_equipment_connected("Dome"),
    ),
    NinaButtonDescription(
        key="dome_open",
        translation_key="dome_open",
        icon="mdi:home-roof",
        action=lambda api: api.dome_open(),
        available_when=_equipment_connected("Dome"),
    ),
    NinaButtonDescription(
        key="dome_close",
        translation_key="dome_close",
        icon="mdi:home-import-outline",
        action=lambda api: api.dome_close(),
        available_when=_equipment_connected("Dome"),
    ),
    NinaButtonDescription(
        key="dome_park",
        translation_key="dome_park",
        icon="mdi:parking",
        action=lambda api: api.dome_park(),
        available_when=_equipment_connected("Dome"),
    ),
    # --- Sequence (existing) --- #
    NinaButtonDescription(
        key="sequence_start",
        translation_key="sequence_start",
        icon="mdi:play-circle",
        action=lambda api: api.sequence_start(),
        available_when=_sequence_idle,
    ),
    NinaButtonDescription(
        key="sequence_stop",
        translation_key="sequence_stop",
        icon="mdi:stop-circle",
        action=lambda api: api.sequence_stop(),
        available_when=_sequence_running,
    ),
    NinaButtonDescription(
        key="plate_solve",
        translation_key="plate_solve",
        icon="mdi:crosshairs-gps",
        action=lambda api: api.plate_solve(),
        available_when=_equipment_connected("Camera"),
    ),
)


class NinaButton(NinaEntity, ButtonEntity):
    """One-shot NINA action button."""

    entity_description: NinaButtonDescription

    def __init__(self, coordinator: NinaCoordinator, description: NinaButtonDescription) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{description.key}"

    @property
    def available(self) -> bool:
        if not super().available:
            return False
        gate = self.entity_description.available_when
        if gate is None:
            return True
        return gate(self.coordinator.data or {})

    async def async_press(self) -> None:
        """Trigger the action on NINA."""
        try:
            await self.entity_description.action(self.coordinator.api_client)
        except Exception as err:  # noqa: BLE001
            _LOGGER.error("NINA action %s failed: %s", self.entity_description.key, err)
            raise
        # Force a refresh so dependent buttons (start/stop) flip availability quickly.
        await self.coordinator.async_request_refresh()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the NINA button platform."""
    coordinator: NinaCoordinator = entry.runtime_data
    async_add_entities(NinaButton(coordinator, desc) for desc in BUTTONS)
