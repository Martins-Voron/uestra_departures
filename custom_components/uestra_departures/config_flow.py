from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_DEPARTURE_COUNT,
    CONF_LINE_FILTER,
    CONF_STOP_ID,
    CONF_STOP_NAME,
    CONF_TRANSPORT_MODE,
    DEFAULT_DEPARTURE_COUNT,
    DEFAULT_TRANSPORT_MODE,
    DOMAIN,
    TRANSPORT_MODES,
)


class UestraConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            line_filter = user_input.get(CONF_LINE_FILTER, "")
            if isinstance(line_filter, str):
                parsed = [x.strip() for x in line_filter.split(",") if x.strip()]
                user_input[CONF_LINE_FILTER] = parsed

            await self.async_set_unique_id(
                f"{user_input[CONF_STOP_ID]}::{user_input[CONF_TRANSPORT_MODE]}"
            )
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=f"{user_input[CONF_STOP_NAME]} ({user_input[CONF_TRANSPORT_MODE]})",
                data=user_input,
            )

        schema = vol.Schema(
            {
                vol.Required(CONF_STOP_NAME): str,
                vol.Required(CONF_STOP_ID): str,
                vol.Required(CONF_TRANSPORT_MODE, default=DEFAULT_TRANSPORT_MODE): vol.In(TRANSPORT_MODES),
                vol.Required(CONF_DEPARTURE_COUNT, default=DEFAULT_DEPARTURE_COUNT): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=10)
                ),
                vol.Optional(CONF_LINE_FILTER, default=""): str,
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema)