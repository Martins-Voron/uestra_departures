import logging
from datetime import datetime, timezone
import aiohttp

_LOGGER = logging.getLogger(__name__)

BASE_URL = "https://abfahrten.uestra.de/proxy2/efa/XML_DM_REQUEST"


class UestraAPI:
    def __init__(self, hass, stop_id, transport_mode):
        self._hass = hass
        self._stop_id = stop_id
        self._transport_mode = transport_mode

    async def fetch_departures(self):
        params = {
            "name_dm": self._stop_id,
            "type_dm": "any",
            "mode": "direct",
            "useRealtime": 1,
            "outputFormat": "rapidJSON",
            "depType": "stopEvents",
            "depSequence": 30,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(BASE_URL, params=params) as response:
                    if response.status != 200:
                        _LOGGER.error("HTTP Fehler: %s", response.status)
                        return []

                    data = await response.json()
                    return self._parse_departures(data)

        except Exception as e:
            _LOGGER.exception("Fehler beim Abrufen der ÜSTRA-Daten: %s", e)
            return []

    def _parse_departures(self, data):
        departures = []

        try:
            now_utc = datetime.now(timezone.utc)

            for dep in data.get("departureList", []):
                line = dep.get("servingLine", {}).get("number")
                destination = dep.get("servingLine", {}).get("direction")

                # Zeit holen
                realtime = dep.get("realDateTime") or dep.get("dateTime")

                if not realtime:
                    continue

                try:
                    dt = datetime(
                        int(realtime["year"]),
                        int(realtime["month"]),
                        int(realtime["day"]),
                        int(realtime["hour"]),
                        int(realtime["minute"]),
                        tzinfo=timezone.utc,
                    )
                except Exception as e:
                    _LOGGER.debug("Zeit parsing fehlgeschlagen: %s", e)
                    continue

                # 🔥 WICHTIG: UTC Vergleich
                if dt <= now_utc:
                    continue

                delay = dep.get("delay", 0)

                departures.append(
                    {
                        "line": line,
                        "destination": destination,
                        "scheduled_time": dt.isoformat(),
                        "realtime_time": dt.isoformat(),
                        "delay_minutes": delay,
                        "transport_mode": self._transport_mode,
                    }
                )

            # Sortieren nach Zeit
            departures.sort(key=lambda x: x["realtime_time"])

            # Nur nächste 3
            return departures[:3]

        except Exception as e:
            _LOGGER.exception("Fehler beim Parsen der Daten: %s", e)
            return []