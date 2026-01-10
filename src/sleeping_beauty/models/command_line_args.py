from dataclasses import dataclass, field
from typing import List, Optional, Set


@dataclass
class CommandLineArgs:
    """
    Structured command-line arguments for the rangesigil pipeline.

    Supports:
    """

    # === Core CLI ===
    command: str  # Subcommand to execute
    config: Optional[str] = None  # Path to YAML config
    debug: bool = False  # Verbose logging

    # Internal: which args were explicitly passed
    _explicit_args: Set[str] = field(default_factory=set)
