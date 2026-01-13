from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Tuple

from sleeping_beauty.core.sleep.sleep_stage import SleepStage


@dataclass(frozen=True)
class SleepStageSegment:
    start: datetime
    end: datetime
    stage: SleepStage


@dataclass(frozen=True)
class SleepStageTimeline:
    source: Literal["sleep_phase_5_min"]
    resolution_seconds: int  # always 300
    segments: Tuple[SleepStageSegment, ...]
