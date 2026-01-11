# src/sleeping_beauty/models/oura/page.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, Optional, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class Page(Generic[T]):
    """
    A single page of results from an Oura collection endpoint.
    """

    data: list[T]
    next_token: Optional[str]
    raw: dict
