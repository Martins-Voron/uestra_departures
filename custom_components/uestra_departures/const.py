from __future__ import annotations

DOMAIN = "uestra_departures"

CONF_STOP_NAME = "stop_name"
CONF_STOP_ID = "stop_id"
CONF_TRANSPORT_MODE = "transport_mode"
CONF_DEPARTURE_COUNT = "departure_count"
CONF_LINE_FILTER = "line_filter"

DEFAULT_DEPARTURE_COUNT = 3
DEFAULT_TRANSPORT_MODE = "stadtbahn"

TRANSPORT_MODES = ["stadtbahn", "bus", "all"]

COORDINATOR_UPDATE_INTERVAL_SECONDS = 60

ATTR_DEPARTURES = "departures"
ATTR_DISRUPTIONS = "disruptions"
ATTR_STOP_NAME = "stop_name"
ATTR_TRANSPORT_MODE = "transport_mode"
ATTR_UPDATED_AT = "updated_at"
ATTR_AFFECTED_LINES = "affected_lines"

SENSOR_DEPARTURES = "departures"
SENSOR_DISRUPTIONS = "disruptions"
BINARY_SENSOR_DISRUPTION_ACTIVE = "disruption_active"