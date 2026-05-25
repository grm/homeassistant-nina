"""Sensor platform for NINA Astrophotography."""

import logging
import math
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import NinaCoordinator
from .entity import NinaEntity

_LOGGER = logging.getLogger(__name__)

SENSOR_DESCRIPTIONS: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="camera_temperature",
        translation_key="camera_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="camera_cooler_power",
        translation_key="camera_cooler_power",
        native_unit_of_measurement="%",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="guider_ra_distance",
        translation_key="guider_ra_distance",
        native_unit_of_measurement="px",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="guider_dec_distance",
        translation_key="guider_dec_distance",
        native_unit_of_measurement="px",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="focuser_position",
        translation_key="focuser_position",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="focuser_temperature",
        translation_key="focuser_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="mount_ra",
        translation_key="mount_ra",
    ),
    SensorEntityDescription(
        key="mount_dec",
        translation_key="mount_dec",
    ),
    SensorEntityDescription(
        key="mount_altitude",
        translation_key="mount_altitude",
        native_unit_of_measurement="°",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="mount_azimuth",
        translation_key="mount_azimuth",
        native_unit_of_measurement="°",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="mount_time_to_flip",
        translation_key="mount_time_to_flip",
        native_unit_of_measurement="min",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="sequence_target",
        translation_key="sequence_target",
    ),
    SensorEntityDescription(
        key="weather_temperature",
        translation_key="weather_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="weather_humidity",
        translation_key="weather_humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        native_unit_of_measurement="%",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="weather_pressure",
        translation_key="weather_pressure",
        device_class=SensorDeviceClass.ATMOSPHERIC_PRESSURE,
        native_unit_of_measurement=UnitOfPressure.HPA,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="weather_dewpoint",
        translation_key="weather_dewpoint",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="weather_wind_speed",
        translation_key="weather_wind_speed",
        device_class=SensorDeviceClass.WIND_SPEED,
        native_unit_of_measurement=UnitOfSpeed.METERS_PER_SECOND,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="weather_sky_quality",
        translation_key="weather_sky_quality",
        native_unit_of_measurement="mag/arcsec²",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="weather_sky_temperature",
        translation_key="weather_sky_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
)


def _safe_float(value: Any) -> float | None:
    """Return None for NaN or non-numeric values."""
    if value is None:
        return None
    if isinstance(value, str):
        if value == "NaN":
            return None
        try:
            value = float(value)
        except ValueError:
            return None
    if isinstance(value, (int, float)):
        if math.isnan(value) or math.isinf(value):
            return None
        return round(value, 2)
    return None


class NinaSensor(NinaEntity, SensorEntity):
    """NINA sensor entity."""

    def __init__(
        self,
        coordinator: NinaCoordinator,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{description.key}"

    @property
    def native_value(self):
        """Return the sensor value."""
        if not self.coordinator.data or "equipment" not in self.coordinator.data:
            return None
        value = self._extract_value(self.entity_description.key)
        _LOGGER.debug("Sensor %s: raw_value=%s", self.entity_description.key, value)
        return value

    def _extract_value(self, key: str):
        """Extract value from coordinator data based on key."""
        equipment = self.coordinator.data.get("equipment", {})
        sequence = self.coordinator.data.get("sequence", {})
        camera = equipment.get("Camera", {})
        mount = equipment.get("Mount", {})
        guider = equipment.get("Guider", {})
        focuser = equipment.get("Focuser", {})
        weather = equipment.get("WeatherData", {})
        last_step = guider.get("LastGuideStep", {})

        mapping = {
            "camera_temperature": lambda: _safe_float(camera.get("Temperature")),
            "camera_cooler_power": lambda: _safe_float(camera.get("CoolerPower")),
            "guider_ra_distance": lambda: _safe_float(last_step.get("RADistanceRaw")),
            "guider_dec_distance": lambda: _safe_float(last_step.get("DECDistanceRaw")),
            "focuser_position": lambda: focuser.get("Position"),
            "focuser_temperature": lambda: _safe_float(focuser.get("Temperature")),
            "mount_ra": lambda: _safe_float(mount.get("RightAscension")),
            "mount_dec": lambda: _safe_float(mount.get("Declination")),
            "mount_altitude": lambda: _safe_float(mount.get("Altitude")),
            "mount_azimuth": lambda: _safe_float(mount.get("Azimuth")),
            "mount_time_to_flip": lambda: _safe_float(mount.get("TimeToMeridianFlip")),
            "sequence_target": lambda: sequence.get("current_target"),
            "weather_temperature": lambda: _safe_float(weather.get("Temperature")),
            "weather_humidity": lambda: _safe_float(weather.get("Humidity")),
            "weather_pressure": lambda: _safe_float(weather.get("Pressure")),
            "weather_dewpoint": lambda: _safe_float(weather.get("DewPoint")),
            "weather_wind_speed": lambda: _safe_float(weather.get("WindSpeed")),
            "weather_sky_quality": lambda: _safe_float(weather.get("SkyQuality")),
            "weather_sky_temperature": lambda: _safe_float(weather.get("SkyTemperature")),
        }

        extractor = mapping.get(key)
        return extractor() if extractor else None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up NINA sensors."""
    coordinator: NinaCoordinator = entry.runtime_data
    async_add_entities(
        NinaSensor(coordinator, description) for description in SENSOR_DESCRIPTIONS
    )
