from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_AFFECTED_LINES,
    ATTR_DEPARTURES,
    ATTR_DISRUPTIONS,
    ATTR_STOP_NAME,
    ATTR_TRANSPORT_MODE,
    ATTR_UPDATED_AT,
    DOMAIN,
    SENSOR_DEPARTURES,
    SENSOR_DISRUPTIONS,
)
from .coordinator import UestraDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: UestraDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            UestraDeparturesSensor(coordinator, entry),
            UestraDisruptionsSensor(coordinator, entry),
        ]
    )


class BaseUestraSensor(CoordinatorEntity[UestraDataUpdateCoordinator], SensorEntity):
    def __init__(self, coordinator: UestraDataUpdateCoordinator, entry: ConfigEntry, suffix: str) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_has_entity_name = True
        self._attr_unique_id = f"{entry.entry_id}_{suffix}"


class UestraDeparturesSensor(BaseUestraSensor):
    def __init__(self, coordinator: UestraDataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, SENSOR_DEPARTURES)
        self._attr_name = "Departures"
        self._attr_icon = "mdi:tram"

    @property
    def native_value(self) -> str:
        if not self.coordinator.data.departures:
            return "no departures"

        next_dep = self.coordinator.data.departures[0]
        return f"{next_dep.line} → {next_dep.destination}"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            ATTR_STOP_NAME: self.coordinator.data.stop_name,
            ATTR_TRANSPORT_MODE: self._entry.data["transport_mode"],
            ATTR_DEPARTURES: [
                {
                    "line": dep.line,
                    "destination": dep.destination,
                    "scheduled_time": dep.scheduled_time,
                    "realtime_time": dep.realtime_time,
                    "delay_minutes": dep.delay_minutes,
                    "transport_mode": dep.transport_mode,
                    "local_time": dep.local_time,
                    "in_minutes": dep.in_minutes,
                }
                for dep in self.coordinator.data.departures
            ],
            ATTR_UPDATED_AT: self.coordinator.data.updated_at,
        }


class UestraDisruptionsSensor(BaseUestraSensor):
    def __init__(self, coordinator: UestraDataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, SENSOR_DISRUPTIONS)
        self._attr_name = "Disruptions"
        self._attr_icon = "mdi:alert-circle-outline"

    @property
    def native_value(self) -> int:
        return len(self.coordinator.data.disruptions)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        messages = []
        affected_lines: list[str] = []

        for disruption in self.coordinator.data.disruptions:
            messages.append(
                {
                    "title": disruption.title,
                    "summary": disruption.summary,
                    "url": disruption.url,
                    "affected_lines": disruption.affected_lines,
                }
            )
            affected_lines.extend(disruption.affected_lines)

        return {
            ATTR_STOP_NAME: self.coordinator.data.stop_name,
            ATTR_DISRUPTIONS: messages,
            ATTR_AFFECTED_LINES: sorted(set(affected_lines)),
            ATTR_UPDATED_AT: self.coordinator.data.updated_at,
        }