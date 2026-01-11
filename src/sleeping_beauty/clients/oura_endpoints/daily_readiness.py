from __future__ import annotations

from datetime import date
from typing import Any

from sleeping_beauty.models.oura.daily_readiness import (
    DailyReadinessScore,
    ReadinessContributors,
)
from sleeping_beauty.models.oura.page import Page


def parse_daily_readiness_item(item: dict[str, Any]) -> DailyReadinessScore:
    day_str = item.get("day")
    if not isinstance(day_str, str):
        raise ValueError("daily_readiness item missing valid 'day'")

    contributors_raw = item.get("contributors") or {}

    contributors = ReadinessContributors(
        activity_balance=contributors_raw.get("activity_balance"),
        body_temperature=contributors_raw.get("body_temperature"),
        hrv_balance=contributors_raw.get("hrv_balance"),
        previous_day_activity=contributors_raw.get("previous_day_activity"),
        previous_night=contributors_raw.get("previous_night"),
        recovery_index=contributors_raw.get("recovery_index"),
        resting_heart_rate=contributors_raw.get("resting_heart_rate"),
        sleep_balance=contributors_raw.get("sleep_balance"),
        sleep_regularity=contributors_raw.get("sleep_regularity"),
    )

    return DailyReadinessScore(
        id=item["id"],
        day=date.fromisoformat(day_str),
        score=item.get("score"),
        temperature_deviation=item.get("temperature_deviation"),
        temperature_trend_deviation=item.get("temperature_trend_deviation"),
        timestamp=item.get("timestamp"),
        contributors=contributors,
        raw=item,
    )


def parse_daily_readiness_page(payload: dict[str, Any]) -> Page[DailyReadinessScore]:
    data = payload.get("data") or []
    parsed = [parse_daily_readiness_item(item) for item in data]

    return Page(
        data=parsed,
        next_token=payload.get("next_token"),
        raw=payload,
    )
