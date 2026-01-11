# sleeping_beauty/models/oura/session.py

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Optional

from .sample_series import SampleSeries


@dataclass(frozen=True, slots=True)
class Session:
    """
    Oura v2 /session resource.

    Represents a moment-based session (e.g. breathing),
    NOT a sleep record.
    """

    id: str
    day: date
    start_datetime: datetime
    end_datetime: datetime

    type: str
    mood: Optional[str]

    heart_rate: Optional[SampleSeries]
    heart_rate_variability: Optional[SampleSeries]
    motion_count: Optional[SampleSeries]

    raw: dict[str, Any]

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "Session":
        return cls(
            id=payload["id"],
            day=date.fromisoformat(payload["day"]),
            start_datetime=datetime.fromisoformat(payload["start_datetime"]),
            end_datetime=datetime.fromisoformat(payload["end_datetime"]),
            type=payload["type"],
            mood=payload.get("mood"),
            heart_rate=(
                SampleSeries.from_payload(payload["heart_rate"])
                if payload.get("heart_rate")
                else None
            ),
            heart_rate_variability=(
                SampleSeries.from_payload(payload["heart_rate_variability"])
                if payload.get("heart_rate_variability")
                else None
            ),
            motion_count=(
                SampleSeries.from_payload(payload["motion_count"])
                if payload.get("motion_count")
                else None
            ),
            raw=payload,
        )
