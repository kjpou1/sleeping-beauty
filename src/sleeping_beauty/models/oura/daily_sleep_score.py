from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass(frozen=True)
class DailySleepScore:
    """
    Daily sleep score summary from Oura v2.
    All scores are in the range 0–100.
    """

    id: str
    day: date

    score: Optional[int]

    # Contributor scores
    deep_sleep: Optional[int]
    efficiency: Optional[int]
    latency: Optional[int]
    rem_sleep: Optional[int]
    restfulness: Optional[int]
    timing: Optional[int]
    total_sleep: Optional[int]

    timestamp: Optional[str]

    raw: dict
