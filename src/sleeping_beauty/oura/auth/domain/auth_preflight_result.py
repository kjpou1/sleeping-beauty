from dataclasses import dataclass
from typing import List


@dataclass
class AuthPreflightReport:
    ok: bool
    messages: List[str]
