from datetime import date, timedelta
from typing import List, Optional

from sleeping_beauty.core.sleep.sleep_stage import SleepStage
from sleeping_beauty.core.sleep.sleep_timeline import (
    SleepStageSegment,
    SleepStageTimeline,
)
from sleeping_beauty.core.sleep.supplemental_sleep_episode import (
    SupplementalSleepEpisode,
)

_SLEEP_STAGE_MAP = {
    "1": SleepStage.DEEP,
    "2": SleepStage.LIGHT,
    "3": SleepStage.REM,
    "4": SleepStage.AWAKE,
}


def build_sleep_stage_timeline(core_sleep) -> Optional[SleepStageTimeline]:
    """
    Build an observational sleep stage timeline from Oura sleep_phase_5_min.

    Rules:
      - 1 char = 5 minutes
      - Anchored at bedtime_start
      - Adjacent identical stages are merged
      - No inference, no smoothing, no gaps invented
    """
    phase_str = getattr(core_sleep, "sleep_phase_5_min", None)
    if not phase_str:
        return None

    start = core_sleep.bedtime_start
    resolution = timedelta(minutes=5)

    segments: List[SleepStageSegment] = []

    current_stage = None
    segment_start = None

    for i, ch in enumerate(phase_str):
        stage = _SLEEP_STAGE_MAP.get(ch)
        if stage is None:
            continue  # defensive: ignore unknown codes silently

        t = start + i * resolution

        if stage != current_stage:
            if current_stage is not None:
                segments.append(
                    SleepStageSegment(
                        start=segment_start,
                        end=t,
                        stage=current_stage,
                    )
                )
            current_stage = stage
            segment_start = t

    # close final segment
    if current_stage is not None and segment_start is not None:
        segments.append(
            SleepStageSegment(
                start=segment_start,
                end=start + len(phase_str) * resolution,
                stage=current_stage,
            )
        )

    return SleepStageTimeline(
        source="sleep_phase_5_min",
        resolution_seconds=300,
        segments=tuple(segments),
    )


def build_supplemental_sleep_episodes(
    *, sleep_docs, core_sleep_id: str, target_day: date
) -> tuple[SupplementalSleepEpisode, ...]:
    """
    Build explicit supplemental (nap) sleep episodes for target_day.
    """
    episodes = []

    for d in sleep_docs:
        if (
            d.day == target_day
            and d.id != core_sleep_id
            and (d.total_sleep_duration or 0) > 0
            and d.bedtime_start
            and d.bedtime_end
        ):
            episodes.append(
                SupplementalSleepEpisode(
                    start=d.bedtime_start,
                    end=d.bedtime_end,
                    duration_seconds=int(d.total_sleep_duration or 0),
                )
            )

    # stable, chronological
    episodes.sort(key=lambda e: e.start)
    return tuple(episodes)
    episodes.sort(key=lambda e: e.start)
    return tuple(episodes)
    episodes.sort(key=lambda e: e.start)
    return tuple(episodes)
