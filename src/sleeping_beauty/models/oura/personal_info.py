from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class PersonalInfo:
    """
    User personal information returned by Oura v2.
    """

    user_id: str

    age: Optional[int]
    biological_sex: Optional[str]

    height: Optional[float]  # meters
    weight: Optional[float]  # kilograms

    email: Optional[str]

    raw: dict
