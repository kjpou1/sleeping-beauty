from __future__ import annotations

from datetime import date
from typing import Any

from sleeping_beauty.models.oura.daily_sleep_score import DailySleepScore
from sleeping_beauty.models.oura.page import Page


def parse_daily_sleep_score_item(item: dict[str, Any]) -> DailySleepScore:
    day_str = item.get("day")
    if not isinstance(day_str, str):
        raise ValueError("daily_sleep item missing valid 'day'")

    contributors = item.get("contributors") or {}

    return DailySleepScore(
        id=item["id"],
        day=date.fromisoformat(day_str),
        score=item.get("score"),
        deep_sleep=contributors.get("deep_sleep"),
        efficiency=contributors.get("efficiency"),
        latency=contributors.get("latency"),
        rem_sleep=contributors.get("rem_sleep"),
        restfulness=contributors.get("restfulness"),
        timing=contributors.get("timing"),
        total_sleep=contributors.get("total_sleep"),
        timestamp=item.get("timestamp"),
        raw=item,
    )


def parse_daily_sleep_score_page(payload: dict[str, Any]) -> Page[DailySleepScore]:
    data = payload.get("data") or []
    parsed = [parse_daily_sleep_score_item(item) for item in data]

    return Page(
        data=parsed,
        next_token=payload.get("next_token"),
        raw=payload,
    )
