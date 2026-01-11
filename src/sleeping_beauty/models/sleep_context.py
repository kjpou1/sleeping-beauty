from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass(frozen=True)
class SleepContext:
    """
    Resolved and validated sleep execution context.

    This represents a single, unambiguous sleep request.
    """

    mode: str  # "view" | "date"
    view: Optional[str]  # today | yesterday | week | month
    start_date: date
    end_date: date
    divider: bool
