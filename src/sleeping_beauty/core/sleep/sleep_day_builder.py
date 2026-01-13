from __future__ import annotations

from datetime import date, time, timedelta
from typing import Optional

from sleeping_beauty.core.sleep.sleep_day_snapshot import SleepDaySnapshot
from sleeping_beauty.core.sleep.sleep_timeline_builder import (
    build_sleep_stage_timeline,
    build_supplemental_sleep_episodes,
)

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
    """
    Build a canonical SleepDaySnapshot for a given day.

    Assumes:
      - sleep_docs are already fetched in an expanded window around target_day
      - daily_sleep + readiness are already resolved for target_day

    Core rule:
      - 'night_start'/'night_end' come from the selected CORE sleep episode
        (bedtime_start/bedtime_end), not from target_day itself.
        This fixes month boundary cases (e.g., Jan 1 should show Dec 31 → Jan 1).
    """
    core_sleep = select_core_sleep(sleep_docs, target_day)

    supplemental_episodes = build_supplemental_sleep_episodes(
        sleep_docs=sleep_docs,
        core_sleep_id=core_sleep.id,
        target_day=target_day,
    )

    supplemental_seconds = compute_supplemental_sleep_seconds(
        sleep_docs=sleep_docs,
        core_sleep_id=core_sleep.id,
        target_day=target_day,
    )

    core_total = core_sleep.total_sleep_duration or 0
    total_24h_seconds = core_total + supplemental_seconds

    # Percentages (avoid div-by-zero)
    rem_seconds = core_sleep.rem_sleep_duration or 0
    deep_seconds = core_sleep.deep_sleep_duration or 0

    rem_pct: Optional[int] = (
        round(100 * rem_seconds / core_total) if core_total > 0 else None
    )
    deep_pct: Optional[int] = (
        round(100 * deep_seconds / core_total) if core_total > 0 else None
    )

    timing_score = getattr(daily_sleep, "timing", 0) or 0
    timing_label = "Optimal" if timing_score >= 90 else f"{timing_score}/100"

    # IMPORTANT: night window is derived from the core sleep episode
    night_start = core_sleep.bedtime_start
    night_end = core_sleep.bedtime_end

    # -------------------------------------------------
    # Timeline construction
    # -------------------------------------------------
    timeline = build_sleep_stage_timeline(core_sleep)

    # -------------------------------------------------
    # Invariant check (NOW valid)
    # -------------------------------------------------
    if timeline and timeline.segments:
        timeline_end = timeline.segments[-1].end
        delta = timeline_end - night_end

        if delta.total_seconds() < 0 or delta.total_seconds() >= 300:
            raise RuntimeError(
                "Sleep timeline invariant violated: "
                f"timeline_end={timeline_end!r} "
                f"night_end={night_end!r} "
                f"delta={delta.total_seconds()}s "
                f"(day={target_day}, sleep_id={core_sleep.id})"
            )

    return SleepDaySnapshot(
        day=target_day,
        night_start=night_start,
        night_end=night_end,
        # --- Core sleep ---
        core_sleep_seconds=core_total,
        time_in_bed_seconds=core_sleep.time_in_bed or 0,
        efficiency_pct=core_sleep.efficiency or 0,
        latency_seconds=getattr(core_sleep, "latency", None),
        rem_seconds=rem_seconds,
        deep_seconds=deep_seconds,
        rem_pct=rem_pct,
        deep_pct=deep_pct,
        avg_hr=getattr(core_sleep, "average_heart_rate", None),
        min_hr=getattr(core_sleep, "lowest_heart_rate", None),
        avg_hrv=getattr(core_sleep, "average_hrv", None),
        # --- Supplemental ---
        supplemental_sleep_seconds=supplemental_seconds,
        total_sleep_24h_seconds=total_24h_seconds,
        # --- Scores ---
        sleep_score=getattr(daily_sleep, "score", 0) or 0,
        readiness_score=getattr(readiness, "score", 0) or 0,
        timing_score=timing_score,
        timing_label=timing_label,
        timeline=timeline,
        supplemental_episodes=supplemental_episodes,
    )


# ================================================================
# Core selection logic
# ================================================================


def select_core_sleep(sleep_docs, target_day: date):
    """
    Canonical core sleep selection:

    1. Prefer sleep that STARTS on (target_day - 1) and ENDS on target_day
       → true overnight sleep crossing midnight
    2. Otherwise fall back to longest sleep ending on target_day
    """
    overnight = [
        d
        for d in sleep_docs
        if (
            d.day == target_day
            and d.bedtime_start.date() == (target_day - timedelta(days=1))
        )
    ]

    if overnight:
        return max(overnight, key=lambda d: d.total_sleep_duration or 0)

    # Fallback: anything ending today
    ending_today = [d for d in sleep_docs if d.day == target_day]
    if not ending_today:
        raise RuntimeError(f"No sleep episodes ending on {target_day}")

    return max(ending_today, key=lambda d: d.total_sleep_duration or 0)


def is_night_sleep(doc) -> bool:
    """
    Night sleep heuristic:
      - Starts after 18:00 OR before noon (cross-midnight window).
    """
    start = doc.bedtime_start.timetz()
    return start >= time(18, 0) or start <= time(12, 0)


# ================================================================
# Supplemental sleep
# ================================================================


def compute_supplemental_sleep_seconds(
    *, sleep_docs, core_sleep_id: str, target_day: date
) -> int:
    """
    Supplemental sleep should only count episodes belonging to target_day
    (doc.day == target_day) excluding the selected core sleep.
    """
    supplemental = [
        d
        for d in sleep_docs
        if (
            d.day == target_day
            and d.id != core_sleep_id
            and (d.total_sleep_duration or 0) > 0
        )
    ]
    return int(sum(d.total_sleep_duration or 0 for d in supplemental))
