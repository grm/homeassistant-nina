"""Base entity for NINA integration."""

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import NinaCoordinator


class NinaEntity(CoordinatorEntity[NinaCoordinator]):
    """Base class for NINA entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: NinaCoordinator) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.config_entry.entry_id)},
            name="NINA",
            manufacturer="NINA",
            model="Astrophotography Suite",
        )
