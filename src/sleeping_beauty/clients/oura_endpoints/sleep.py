from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sleeping_beauty.models.oura.page import Page
from sleeping_beauty.models.oura.sleep import (
    SeriesSample,
    SleepDocument,
    SleepDocumentPage,
    SleepReadiness,
    SleepReadinessContributors,
)

# ---------------------------------------------------------------------------
# Small parsing helpers (kept local, as in daily_sleep_score)
# ---------------------------------------------------------------------------


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def _parse_datetime(value: str) -> datetime:
    # Normalize trailing Z for Python 3.12
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


# ---------------------------------------------------------------------------
# Nested object parsers
# ---------------------------------------------------------------------------


def parse_series_sample(item: dict[str, Any]) -> SeriesSample:
    return SeriesSample(
        interval=float(item["interval"]),
        items=tuple(None if x is None else float(x) for x in item.get("items", [])),
        timestamp=item.get("timestamp"),
        raw=item,
    )


def parse_sleep_readiness_contributors(
    item: dict[str, Any],
) -> SleepReadinessContributors:
    return SleepReadinessContributors(
        activity_balance=item.get("activity_balance"),
        body_temperature=item.get("body_temperature"),
        hrv_balance=item.get("hrv_balance"),
        previous_day_activity=item.get("previous_day_activity"),
        previous_night=item.get("previous_night"),
        recovery_index=item.get("recovery_index"),
        resting_heart_rate=item.get("resting_heart_rate"),
        sleep_balance=item.get("sleep_balance"),
        raw=item,
    )


def parse_sleep_readiness(item: dict[str, Any]) -> SleepReadiness:
    contributors = item.get("contributors") or {}

    return SleepReadiness(
        contributors=parse_sleep_readiness_contributors(contributors),
        score=item.get("score"),
        temperature_deviation=item.get("temperature_deviation"),
        temperature_trend_deviation=item.get("temperature_trend_deviation"),
        raw=item,
    )


# ---------------------------------------------------------------------------
# Core sleep document parser
# ---------------------------------------------------------------------------


def parse_sleep_document(item: dict[str, Any]) -> SleepDocument:
    day_str = item.get("day")
    if not isinstance(day_str, str):
        raise ValueError("sleep document missing valid 'day'")

    return SleepDocument(
        id=item["id"],
        day=_parse_date(day_str),
        period=item.get("period"),
        type=item.get("type"),
        bedtime_start=_parse_datetime(item["bedtime_start"]),
        bedtime_end=_parse_datetime(item["bedtime_end"]),
        time_in_bed=item.get("time_in_bed"),
        total_sleep_duration=item.get("total_sleep_duration"),
        latency=item.get("latency"),
        awake_time=item.get("awake_time"),
        deep_sleep_duration=item.get("deep_sleep_duration"),
        light_sleep_duration=item.get("light_sleep_duration"),
        rem_sleep_duration=item.get("rem_sleep_duration"),
        efficiency=item.get("efficiency"),
        restless_periods=item.get("restless_periods"),
        movement_30_sec=item.get("movement_30_sec"),
        sleep_phase_5_min=item.get("sleep_phase_5_min"),
        average_breath=item.get("average_breath"),
        average_heart_rate=item.get("average_heart_rate"),
        average_hrv=item.get("average_hrv"),
        lowest_heart_rate=item.get("lowest_heart_rate"),
        heart_rate=parse_series_sample(item["heart_rate"]),
        hrv=parse_series_sample(item["hrv"]),
        readiness=parse_sleep_readiness(item["readiness"]),
        sleep_score_delta=item.get("sleep_score_delta"),
        readiness_score_delta=item.get("readiness_score_delta"),
        sleep_algorithm_version=item.get("sleep_algorithm_version"),
        sleep_analysis_reason=item.get("sleep_analysis_reason"),
        low_battery_alert=item.get("low_battery_alert"),
        raw=item,
    )


# ---------------------------------------------------------------------------
# Page parser (matches daily_sleep_score exactly)
# ---------------------------------------------------------------------------


def parse_sleep_document_page(payload: dict[str, Any]) -> Page[SleepDocument]:
    data = payload.get("data") or []
    parsed = [parse_sleep_document(item) for item in data]

    return Page(
        data=parsed,
        next_token=payload.get("next_token"),
        raw=payload,
    )
