# sleeping_beauty/models/oura/heartrate.py

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class HeartRateSample:
    """
    Single heart-rate time-series sample from Oura.

    Represents a 5-minute interval measurement.
    """

    bpm: int
    source: str
    timestamp: datetime


# sleeping_beauty/models/oura/heartrate.py


@dataclass(frozen=True)
class HeartRateTimeSeriesPage:
    data: list[HeartRateSample]
    next_token: str | None
    raw: dict[str, Any]
