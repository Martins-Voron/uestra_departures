from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
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
            "canChangeMOT": "0",
            "coordOutputFormat": "WGS84[dd.ddddd]",
            "deleteAssignedStops_dm": "1",
            "depSequence": "30",
            "depType": "stopEvents",
            "doNotSearchForStops": "1",
            "genMaps": "0",
            "imparedOptionsActive": "1",
            "inclMOT_1": "true",
            "inclMOT_2": "true",
            "inclMOT_3": "true",
            "inclMOT_4": "true",
            "inclMOT_5": "true",
            "inclMOT_6": "true",
            "inclMOT_7": "true",
            "inclMOT_8": "true",
            "inclMOT_9": "true",
            "inclMOT_10": "true",
            "inclMOT_11": "true",
            "inclMOT_13": "true",
            "inclMOT_14": "true",
            "inclMOT_15": "true",
            "inclMOT_16": "true",
            "inclMOT_17": "true",
            "inclMOT_18": "true",
            "inclMOT_19": "true",
            "includeCompleteStopSeq": "1",
            "includedMeans": "checkbox",
            "itOptionsActive": "1",
            "itdDateTimeDepArr": "dep",
            "language": "de",
            "locationServerActive": "1",
            "maxTimeLoop": "1",
            "mergeDep": "1",
            "mode": "direct",
            "outputFormat": "rapidJSON",
            "ptOptionsActive": "1",
            "serverInfo": "1",
            "sl3plusDMMacro": "1",
            "type_dm": "any",
            "useAllStops": "1",
            "useProxFootSearch": "0",
            "useRealtime": "1",
            "version": "10.5.17.3",
            "c": "4",
            "name_dm": stop_id,
        }

        headers = {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"https://abfahrten.uestra.de/?h={stop_id}",
        }

        async with self._session.get(
            UESTRA_DEPARTURES_API_URL,
            params=params,
            headers=headers,
            timeout=DEFAULT_TIMEOUT,
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()

        if not isinstance(data, dict):
            raise ValueError("Unexpected API response format")

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

                # Vergangene Abfahrten ignorieren
                if effective_dt <= datetime.now(effective_dt.tzinfo):
                    continue

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
        raw_departures = payload.get("departures", [])
        disruptions: list[Disruption] = []
        seen_ids: set[str] = set()

        for dep in raw_departures:
            line_name = str(dep.get("line", "")).strip()
            line_number = str(dep.get("number", "")).strip()

            detected_mode = self._detect_transport_mode(line_name)

            if not self._matches_transport_mode(detected_mode, transport_mode):
                continue

            if line_filter and line_number not in line_filter and line_name not in line_filter:
                continue

            for info in dep.get("infos", []):
                info_id = str(info.get("id", "")).strip()
                if info_id and info_id in seen_ids:
                    continue

                title = str(info.get("titel", "")).strip()
                content = str(info.get("content", "")).strip()

                if not title and not content:
                    continue

                disruptions.append(
                    Disruption(
                        title=title or f"Meldung Linie {line_number or line_name}",
                        summary=content,
                        url=None,
                        affected_lines=[line_number or line_name],
                    )
                )

                if info_id:
                    seen_ids.add(info_id)

        return disruptions

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