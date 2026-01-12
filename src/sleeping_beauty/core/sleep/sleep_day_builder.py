# src/sleeping_beauty/core/sleep/sleep_day_builder.py

from datetime import date, time, timedelta
from typing import Iterable

from sleeping_beauty.core.sleep.sleep_day_snapshot import SleepDaySnapshot

# ================================================================
# Public API
# ================================================================


async def build_sleep_day_snapshot(
    *,
    target_day: date,
    sleep_docs: list,
    daily_sleep,
    readiness,
) -> SleepDaySnapshot:
    core = select_core_sleep(sleep_docs, target_day)
    supplemental, supplemental_seconds = compute_supplemental_sleep(
        sleep_docs, core, target_day
    )

    total_24h = (core.total_sleep_duration or 0) + supplemental_seconds

    rem_pct = (
        round(100 * core.rem_sleep_duration / core.total_sleep_duration)
        if core.rem_sleep_duration and core.total_sleep_duration
        else None
    )

    deep_pct = (
        round(100 * core.deep_sleep_duration / core.total_sleep_duration)
        if core.deep_sleep_duration and core.total_sleep_duration
        else None
    )

    timing_label = (
        "Optimal" if daily_sleep.timing >= 90 else f"{daily_sleep.timing}/100"
    )

    return SleepDaySnapshot(
        day=target_day,
        night_start=core.bedtime_start,
        night_end=core.bedtime_end,
        core_sleep_seconds=core.total_sleep_duration or 0,
        time_in_bed_seconds=core.time_in_bed or 0,
        efficiency_pct=core.efficiency,
        latency_seconds=core.latency,
        rem_seconds=core.rem_sleep_duration or 0,
        deep_seconds=core.deep_sleep_duration or 0,
        rem_pct=rem_pct,
        deep_pct=deep_pct,
        avg_hr=core.average_heart_rate,
        min_hr=core.lowest_heart_rate,
        avg_hrv=core.average_hrv,
        supplemental_sleep_seconds=supplemental_seconds,
        total_sleep_24h_seconds=total_24h,
        sleep_score=daily_sleep.score,
        readiness_score=readiness.score,
        timing_score=daily_sleep.timing,
        timing_label=timing_label,
    )


# ================================================================
# Core selection logic
# ================================================================


def select_core_sleep(sleep_docs, target_day: date):
    ending_today = [d for d in sleep_docs if d.day == target_day]

    if not ending_today:
        raise RuntimeError(f"No sleep episodes ending on {target_day}")

    long_sleeps = [d for d in ending_today if d.type == "long_sleep"]
    if long_sleeps:
        return max(long_sleeps, key=lambda d: d.total_sleep_duration or 0)

    night_sleeps = [d for d in ending_today if is_night_sleep(d)]
    if night_sleeps:
        return max(night_sleeps, key=lambda d: d.total_sleep_duration or 0)

    return max(ending_today, key=lambda d: d.total_sleep_duration or 0)


def is_night_sleep(doc) -> bool:
    start = doc.bedtime_start.timetz()
    return start >= time(18, 0) or start <= time(12, 0)


# ================================================================
# Supplemental sleep
# ================================================================


def compute_supplemental_sleep(
    sleep_docs,
    core_sleep,
    target_day: date,
):
    """
    Supplemental sleep = any non-core sleep episode
    that ENDS on target_day.
    """
    supplemental = [
        d
        for d in sleep_docs
        if (
            d.day == target_day
            and d.id != core_sleep.id
            and (d.total_sleep_duration or 0) > 0
        )
    ]

    total_seconds = sum(d.total_sleep_duration or 0 for d in supplemental)
    return supplemental, total_seconds
