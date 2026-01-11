from __future__ import annotations

from datetime import datetime
from typing import Any

from sleeping_beauty.models.oura.heartrate import HeartRateSample
from sleeping_beauty.models.oura.page import Page


def _parse_utc_timestamp(value: str) -> datetime:
    if value.endswith("Z"):
        value = value.replace("Z", "+00:00")
    return datetime.fromisoformat(value)


def parse_heartrate_item(item: dict[str, Any]) -> HeartRateSample:
    """
    Parse a single heart-rate time-series sample.

    Expected shape (ground-truthed):
    {
        "bpm": int,
        "source": str,
        "timestamp": str (ISO 8601)
    }
    """
    try:
        bpm = item["bpm"]
        source = item["source"]
        timestamp_str = item["timestamp"]
    except KeyError as exc:
        raise ValueError(f"heartrate item missing required field: {exc}") from exc

    if not isinstance(bpm, int):
        raise ValueError("heartrate item 'bpm' must be int")

    if not isinstance(source, str):
        raise ValueError("heartrate item 'source' must be str")

    if not isinstance(timestamp_str, str):
        raise ValueError("heartrate item 'timestamp' must be str")

    return HeartRateSample(
        bpm=bpm,
        source=source,
        timestamp=_parse_utc_timestamp(timestamp_str),
    )


def parse_heartrate_page(payload: dict[str, Any]) -> Page[HeartRateSample]:
    """
    Parse a paginated heart-rate time-series response.
    """
    data = payload.get("data") or []
    parsed = [parse_heartrate_item(item) for item in data]

    return Page(
        data=parsed,
        next_token=payload.get("next_token"),
        raw=payload,
    )
