from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Mapping, Tuple

# -------------------------
# Parsing helpers (boring, explicit)
# -------------------------


def _parse_date(value: str) -> date:
    # Oura uses YYYY-MM-DD
    return date.fromisoformat(value)


def _parse_datetime(value: str) -> datetime:
    # Oura typically returns ISO 8601 strings.
    # Normalize trailing Z for Python 3.12 compatibility.
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


# -------------------------
# Series / Sample DTO
# -------------------------


@dataclass(frozen=True, slots=True)
class SeriesSample:
    interval: float
    items: Tuple[float, ...]
    timestamp: str
    raw: Mapping[str, Any]

    @staticmethod
    def from_api(payload: Mapping[str, Any]) -> "SeriesSample":
        return SeriesSample(
            interval=float(payload["interval"]),
            items=tuple(float(x) for x in payload.get("items", [])),
            timestamp=str(payload["timestamp"]),
            raw=payload,
        )


# -------------------------
# Readiness DTOs (sleep-scoped)
# -------------------------


@dataclass(frozen=True, slots=True)
class SleepReadinessContributors:
    activity_balance: int
    body_temperature: int
    hrv_balance: int
    previous_day_activity: int
    previous_night: int
    recovery_index: int
    resting_heart_rate: int
    sleep_balance: int
    raw: Mapping[str, Any]

    @staticmethod
    def from_api(payload: Mapping[str, Any]) -> "SleepReadinessContributors":
        return SleepReadinessContributors(
            activity_balance=int(payload["activity_balance"]),
            body_temperature=int(payload["body_temperature"]),
            hrv_balance=int(payload["hrv_balance"]),
            previous_day_activity=int(payload["previous_day_activity"]),
            previous_night=int(payload["previous_night"]),
            recovery_index=int(payload["recovery_index"]),
            resting_heart_rate=int(payload["resting_heart_rate"]),
            sleep_balance=int(payload["sleep_balance"]),
            raw=payload,
        )


@dataclass(frozen=True, slots=True)
class SleepReadiness:
    contributors: SleepReadinessContributors
    score: int
    temperature_deviation: float
    temperature_trend_deviation: float
    raw: Mapping[str, Any]

    @staticmethod
    def from_api(payload: Mapping[str, Any]) -> "SleepReadiness":
        return SleepReadiness(
            contributors=SleepReadinessContributors.from_api(payload["contributors"]),
            score=int(payload["score"]),
            temperature_deviation=float(payload["temperature_deviation"]),
            temperature_trend_deviation=float(payload["temperature_trend_deviation"]),
            raw=payload,
        )


# -------------------------
# Core Sleep Document DTO
# -------------------------


@dataclass(frozen=True, slots=True)
class SleepDocument:
    # Identity
    id: str
    day: date
    period: int
    type: str

    # Timing
    bedtime_start: datetime
    bedtime_end: datetime
    time_in_bed: int
    total_sleep_duration: int
    latency: int

    # Sleep stages (seconds)
    awake_time: int
    deep_sleep_duration: int
    light_sleep_duration: int
    rem_sleep_duration: int

    # Quality / structure
    efficiency: int
    restless_periods: int
    movement_30_sec: str
    sleep_phase_5_min: str

    # Physiology
    average_breath: float
    average_heart_rate: float
    average_hrv: float
    lowest_heart_rate: int
    heart_rate: SeriesSample
    hrv: SeriesSample

    # Readiness linkage
    readiness: SleepReadiness
    sleep_score_delta: int
    readiness_score_delta: int

    # Metadata
    sleep_algorithm_version: str
    sleep_analysis_reason: str
    low_battery_alert: bool

    # Raw payload preservation
    raw: Mapping[str, Any]

    @staticmethod
    def from_api(payload: Mapping[str, Any]) -> "SleepDocument":
        return SleepDocument(
            id=str(payload["id"]),
            day=_parse_date(payload["day"]),
            period=int(payload["period"]),
            type=str(payload["type"]),
            bedtime_start=_parse_datetime(payload["bedtime_start"]),
            bedtime_end=_parse_datetime(payload["bedtime_end"]),
            time_in_bed=int(payload["time_in_bed"]),
            total_sleep_duration=int(payload["total_sleep_duration"]),
            latency=int(payload["latency"]),
            awake_time=int(payload["awake_time"]),
            deep_sleep_duration=int(payload["deep_sleep_duration"]),
            light_sleep_duration=int(payload["light_sleep_duration"]),
            rem_sleep_duration=int(payload["rem_sleep_duration"]),
            efficiency=int(payload["efficiency"]),
            restless_periods=int(payload["restless_periods"]),
            movement_30_sec=str(payload["movement_30_sec"]),
            sleep_phase_5_min=str(payload["sleep_phase_5_min"]),
            average_breath=float(payload["average_breath"]),
            average_heart_rate=float(payload["average_heart_rate"]),
            average_hrv=float(payload["average_hrv"]),
            lowest_heart_rate=int(payload["lowest_heart_rate"]),
            heart_rate=SeriesSample.from_api(payload["heart_rate"]),
            hrv=SeriesSample.from_api(payload["hrv"]),
            readiness=SleepReadiness.from_api(payload["readiness"]),
            sleep_score_delta=int(payload["sleep_score_delta"]),
            readiness_score_delta=int(payload["readiness_score_delta"]),
            sleep_algorithm_version=str(payload["sleep_algorithm_version"]),
            sleep_analysis_reason=str(payload["sleep_analysis_reason"]),
            low_battery_alert=bool(payload["low_battery_alert"]),
            raw=payload,
        )


# -------------------------
# Collection wrapper DTO
# -------------------------


@dataclass(frozen=True, slots=True)
class SleepDocumentPage:
    data: Tuple[SleepDocument, ...]
    next_token: str | None
    raw: Mapping[str, Any]

    @staticmethod
    def from_api(payload: Mapping[str, Any]) -> "SleepDocumentPage":
        return SleepDocumentPage(
            data=tuple(
                SleepDocument.from_api(item) for item in payload.get("data", [])
            ),
            next_token=payload.get("next_token"),
            raw=payload,
        )
