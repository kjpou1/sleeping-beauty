# sleeping_beauty/core/sleep/supplemental_sleep_episode.py

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class SupplementalSleepEpisode:
    start: datetime
    end: datetime
    duration_seconds: int
