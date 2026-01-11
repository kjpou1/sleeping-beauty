from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Mapping, Optional


@dataclass(frozen=True)
class ReadinessContributors:
    """
    Contributor subscores for the daily readiness score.

    All fields are nullable integers. The API may omit or null individual
    contributors depending on data availability.
    """

    activity_balance: Optional[int]
    body_temperature: Optional[int]
    hrv_balance: Optional[int]
    previous_day_activity: Optional[int]
    previous_night: Optional[int]
    recovery_index: Optional[int]
    resting_heart_rate: Optional[int]
    sleep_balance: Optional[int]
    sleep_regularity: Optional[int]


@dataclass(frozen=True)
class DailyReadinessScore:
    """
    Daily readiness score document.

    This is a score-oriented summary object, not raw physiological data.
    It mirrors the semantics of other Oura v2 daily score documents
    (e.g. daily_sleep).
    """

    # Identity
    id: str
    day: date

    # Score
    score: Optional[int]

    # Temperature signals (in °C, nullable)
    temperature_deviation: Optional[float]
    temperature_trend_deviation: Optional[float]

    timestamp: Optional[str]

    # Contributors
    contributors: ReadinessContributors

    # Raw payload preservation
    raw: Mapping[str, Any]
