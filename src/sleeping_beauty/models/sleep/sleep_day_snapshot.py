from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional


@dataclass(frozen=True)
class SleepDaySnapshot:
    day: date
    night_start: datetime
    night_end: datetime

    # --- Core sleep ---
    core_sleep_seconds: int
    time_in_bed_seconds: int
    efficiency_pct: int
    latency_seconds: Optional[int]

    rem_seconds: int
    deep_seconds: int
    rem_pct: Optional[int]
    deep_pct: Optional[int]

    avg_hr: Optional[float]
    min_hr: Optional[int]
    avg_hrv: Optional[int]

    # --- Supplemental ---
    supplemental_sleep_seconds: int
    total_sleep_24h_seconds: int

    # --- Scores ---
    sleep_score: int
    readiness_score: int
    timing_score: int
    timing_label: str
