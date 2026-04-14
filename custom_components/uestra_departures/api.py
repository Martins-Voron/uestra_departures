from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import logging
from typing import Any

from aiohttp import ClientSession

_LOGGER = logging.getLogger(__name__)

UESTRA_DEPARTURES_API_URL = "https://abfahrten.uestra.de/proxy2/efa/XML_DM_REQUEST"
DEFAULT_TIMEOUT = 20


@dataclass
class Departure:
    line: str
    destination: str
    scheduled_time: str
    realtime_time: str | None
    delay_minutes: int | None
    transport_mode: str
    local_time: str
    in_minutes: int


@dataclass
class Disruption:
    title: str
    summary: str
    url: str | None
    affected_lines: list[str]


@dataclass
class UestraData:
    stop_name: str
    departures: list[Departure]
    disruptions: list[Disruption]
    updated_at: str


class UestraApiClient:
    def __init__(self, session: ClientSession) -> None:
        self._session = session

    async def async_fetch_data(
        self,
        stop_name: str,
        stop_id: str,
        transport_mode: str,
        departure_count: int,
        line_filter: list[str] | None = None,
    ) -> UestraData:
        raw = await self._async_fetch_departure_payload(stop_id=stop_id)

        departures = self._parse_departures(
            payload=raw,
            transport_mode=transport_mode,
            departure_count=departure_count,
            line_filter=line_filter or [],
        )

        disruptions = self._parse_disruptions(
            payload=raw,
            transport_mode=transport_mode,
            line_filter=line_filter or [],
        )

        return UestraData(
            stop_name=raw.get("stop", stop_name),
            departures=departures,
            disruptions=disruptions,
            updated_at=datetime.now().isoformat(),
        )

    async def _async_fetch_departure_payload(self, stop_id: str) -> dict[str, Any]:
        params = {
            "name_dm": stop_id,
            "type_dm": "any",
            "mode": "direct",
            "useRealtime": "1",
            "outputFormat": "rapidJSON",
            "depType": "stopEvents",
            "depSequence": "30",
        }

        headers = {
            "Accept": "application/json",
            "X-Requested-With": "XMLHttpRequest",
        }

        async with self._session.get(
            UESTRA_DEPARTURES_API_URL,
            params=params,
            headers=headers,
            timeout=DEFAULT_TIMEOUT,
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()

        return data

    def _parse_departures(
        self,
        payload: dict[str, Any],
        transport_mode: str,
        departure_count: int,
        line_filter: list[str],
    ) -> list[Departure]:
        raw_departures = payload.get("departures", [])
        parsed: list[Departure] = []

        now_utc = datetime.now(timezone.utc)
        now_local = datetime.now().astimezone()

        for dep in raw_departures:
            line_name = str(dep.get("line", "")).strip()
            line_number = str(dep.get("number", "")).strip()
            destination = str(dep.get("destination", "")).strip()

            detected_mode = self._detect_transport_mode(line_name)

            if not self._matches_transport_mode(detected_mode, transport_mode):
                continue

            if line_filter and line_number not in line_filter and line_name not in line_filter:
                continue

            for event in dep.get("events", []):
                planned_time = event.get("plannedTime")
                estimated_time = event.get("estimated_time")

                if not planned_time:
                    continue

                effective_time = estimated_time or planned_time
                effective_dt = self._parse_iso_datetime(effective_time)

                # Nur zukünftige
                if effective_dt <= now_utc:
                    continue

                # 🔥 Neue Features
                local_dt = effective_dt.astimezone()
                in_minutes = int((effective_dt - now_utc).total_seconds() // 60)

                delay_minutes = self._calculate_delay_minutes(
                    planned_time=planned_time,
                    estimated_time=estimated_time,
                )

                parsed.append(
                    Departure(
                        line=line_number or line_name,
                        destination=destination,
                        scheduled_time=planned_time,
                        realtime_time=estimated_time,
                        delay_minutes=delay_minutes,
                        transport_mode=detected_mode,
                        local_time=local_dt.strftime("%H:%M"),
                        in_minutes=in_minutes,
                    )
                )

        parsed.sort(
            key=lambda d: self._parse_iso_datetime(d.realtime_time or d.scheduled_time)
        )

        return parsed[:departure_count]

    def _parse_disruptions(
        self,
        payload: dict[str, Any],
        transport_mode: str,
        line_filter: list[str],
    ) -> list[Disruption]:
        return []

    @staticmethod
    def _detect_transport_mode(line_name: str) -> str:
        line_name_lower = line_name.lower()
        if "stadtbahn" in line_name_lower:
            return "stadtbahn"
        if "bus" in line_name_lower:
            return "bus"
        return "all"

    @staticmethod
    def _matches_transport_mode(detected_mode: str, wanted_mode: str) -> bool:
        if wanted_mode == "all":
            return True
        return detected_mode == wanted_mode

    @staticmethod
    def _parse_iso_datetime(value: str) -> datetime:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))

    def _calculate_delay_minutes(
        self,
        planned_time: str,
        estimated_time: str | None,
    ) -> int | None:
        if not estimated_time:
            return None

        planned = self._parse_iso_datetime(planned_time)
        estimated = self._parse_iso_datetime(estimated_time)
        delta = estimated - planned
        return int(delta.total_seconds() // 60)