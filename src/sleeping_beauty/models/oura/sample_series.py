# sleeping_beauty/models/oura/sample_series.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class SampleSeries:
    interval: int
    items: list[float]
    timestamp: str

    raw: dict[str, Any]

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "SampleSeries":
        return cls(
            interval=payload["interval"],
            items=payload["items"],
            timestamp=payload["timestamp"],
            raw=payload,
        )
