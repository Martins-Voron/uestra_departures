from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import BINARY_SENSOR_DISRUPTION_ACTIVE, DOMAIN
from .coordinator import UestraDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: UestraDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([UestraDisruptionActiveBinarySensor(coordinator, entry)])


class UestraDisruptionActiveBinarySensor(
    CoordinatorEntity[UestraDataUpdateCoordinator], BinarySensorEntity
):
    def __init__(self, coordinator: UestraDataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_has_entity_name = True
        self._attr_name = "Disruption Active"
        self._attr_icon = "mdi:alert"
        self._attr_unique_id = f"{entry.entry_id}_{BINARY_SENSOR_DISRUPTION_ACTIVE}"

    @property
    def is_on(self) -> bool:
        return len(self.coordinator.data.disruptions) > 0