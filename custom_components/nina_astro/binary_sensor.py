"""Binary sensor platform for NINA Astrophotography."""

import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import NinaCoordinator
from .entity import NinaEntity

_LOGGER = logging.getLogger(__name__)

BINARY_SENSOR_DESCRIPTIONS: tuple[BinarySensorEntityDescription, ...] = (
    BinarySensorEntityDescription(
        key="camera_connected",
        translation_key="camera_connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
    ),
    BinarySensorEntityDescription(
        key="mount_connected",
        translation_key="mount_connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
    ),
    BinarySensorEntityDescription(
        key="guider_connected",
        translation_key="guider_connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
    ),
    BinarySensorEntityDescription(
        key="focuser_connected",
        translation_key="focuser_connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
    ),
    BinarySensorEntityDescription(
        key="filterwheel_connected",
        translation_key="filterwheel_connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
    ),
    BinarySensorEntityDescription(
        key="dome_connected",
        translation_key="dome_connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
    ),
    BinarySensorEntityDescription(
        key="rotator_connected",
        translation_key="rotator_connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
    ),
    BinarySensorEntityDescription(
        key="weather_connected",
        translation_key="weather_connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
    ),
    BinarySensorEntityDescription(
        key="safety_monitor_connected",
        translation_key="safety_monitor_connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
    ),
    BinarySensorEntityDescription(
        key="safety_is_safe",
        translation_key="safety_is_safe",
        device_class=BinarySensorDeviceClass.SAFETY,
    ),
    BinarySensorEntityDescription(
        key="sequence_running",
        translation_key="sequence_running",
        device_class=BinarySensorDeviceClass.RUNNING,
    ),
    BinarySensorEntityDescription(
        key="mount_tracking",
        translation_key="mount_tracking",
    ),
    BinarySensorEntityDescription(
        key="mount_slewing",
        translation_key="mount_slewing",
        device_class=BinarySensorDeviceClass.MOVING,
    ),
    BinarySensorEntityDescription(
        key="mount_at_park",
        translation_key="mount_at_park",
    ),
    BinarySensorEntityDescription(
        key="camera_exposing",
        translation_key="camera_exposing",
        device_class=BinarySensorDeviceClass.RUNNING,
    ),
    BinarySensorEntityDescription(
        key="camera_cooler_on",
        translation_key="camera_cooler_on",
    ),
)


class NinaBinarySensor(NinaEntity, BinarySensorEntity):
    """NINA binary sensor entity."""

    def __init__(
        self,
        coordinator: NinaCoordinator,
        description: BinarySensorEntityDescription,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{description.key}"

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        if not self.coordinator.data or "equipment" not in self.coordinator.data:
            return None
        value = self._extract_value(self.entity_description.key)
        _LOGGER.debug("Binary sensor %s: value=%s", self.entity_description.key, value)
        return value

    def _extract_value(self, key: str) -> bool | None:
        """Extract value from coordinator data."""
        equipment = self.coordinator.data.get("equipment", {})
        sequence = self.coordinator.data.get("sequence", {})

        mapping: dict[str, Any] = {
            "camera_connected": lambda: equipment.get("Camera", {}).get("Connected", False),
            "mount_connected": lambda: equipment.get("Mount", {}).get("Connected", False),
            "guider_connected": lambda: equipment.get("Guider", {}).get("Connected", False),
            "focuser_connected": lambda: equipment.get("Focuser", {}).get("Connected", False),
            "filterwheel_connected": lambda: equipment.get("FilterWheel", {}).get("Connected", False),
            "dome_connected": lambda: equipment.get("Dome", {}).get("Connected", False),
            "rotator_connected": lambda: equipment.get("Rotator", {}).get("Connected", False),
            "weather_connected": lambda: equipment.get("WeatherData", {}).get("Connected", False),
            "safety_monitor_connected": lambda: equipment.get("SafetyMonitor", {}).get("Connected", False),
            "safety_is_safe": lambda: equipment.get("SafetyMonitor", {}).get("IsSafe", False),
            "sequence_running": lambda: sequence.get("running", False),
            "mount_tracking": lambda: equipment.get("Mount", {}).get("TrackingEnabled", False),
            "mount_slewing": lambda: equipment.get("Mount", {}).get("Slewing", False),
            "mount_at_park": lambda: equipment.get("Mount", {}).get("AtPark", False),
            "camera_exposing": lambda: equipment.get("Camera", {}).get("IsExposing", False),
            "camera_cooler_on": lambda: equipment.get("Camera", {}).get("CoolerOn", False),
        }

        extractor = mapping.get(key)
        return extractor() if extractor else None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up NINA binary sensors."""
    coordinator: NinaCoordinator = entry.runtime_data
    async_add_entities(
        NinaBinarySensor(coordinator, description)
        for description in BINARY_SENSOR_DESCRIPTIONS
    )
