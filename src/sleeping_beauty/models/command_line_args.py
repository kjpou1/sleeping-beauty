from dataclasses import dataclass, field
from typing import Literal, Optional, Set


@dataclass
class CommandLineArgs:
    """
    Structured command-line arguments for the sleeping-beauty CLI.

    Supports:
    - sleep summary
    """

    # === Core CLI ===
    command: str  # e.g. "sleep"
    subcommand: Optional[str] = None  # e.g. "summary"
    config: Optional[str] = None  # Path to YAML config
    debug: bool = False  # Verbose logging

    # === Sleep summary args ===

    # View-based mode
    view: Optional[Literal["today", "yesterday", "week", "month"]] = None

    # Date-based mode
    start_date: Optional[str] = None  # YYYY-MM-DD
    end_date: Optional[str] = None  # YYYY-MM-DD

    # Output behavior
    divider: bool = False  # Divider between days (multi-day only)

    # Internal: which args were explicitly passed
    _explicit_args: Set[str] = field(default_factory=set)
