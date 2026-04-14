from __future__ import annotations

from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import UestraApiClient, UestraData
from .const import (
    CONF_DEPARTURE_COUNT,
    CONF_LINE_FILTER,
    CONF_STOP_ID,
    CONF_STOP_NAME,
    CONF_TRANSPORT_MODE,
    COORDINATOR_UPDATE_INTERVAL_SECONDS,
    DOMAIN,
)


class UestraDataUpdateCoordinator(DataUpdateCoordinator[UestraData]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.entry = entry
        session = async_get_clientsession(hass)
        self.api = UestraApiClient(session)

        super().__init__(
            hass,
            logger=None,
            name=DOMAIN,
            update_interval=timedelta(seconds=COORDINATOR_UPDATE_INTERVAL_SECONDS),
        )

    async def _async_update_data(self) -> UestraData:
        try:
            return await self.api.async_fetch_data(
                stop_name=self.entry.data[CONF_STOP_NAME],
                stop_id=self.entry.data[CONF_STOP_ID],
                transport_mode=self.entry.data[CONF_TRANSPORT_MODE],
                departure_count=self.entry.data[CONF_DEPARTURE_COUNT],
                line_filter=self.entry.data.get(CONF_LINE_FILTER),
            )
        except Exception as err:
            raise UpdateFailed(str(err)) from err