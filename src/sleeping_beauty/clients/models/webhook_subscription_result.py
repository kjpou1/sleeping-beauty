from dataclasses import dataclass
from typing import Any, Optional


@dataclass(slots=True)
class WebhookSubscriptionResult:
    """
    Result envelope for Oura webhook subscription operations.

    Covers:
    - create
    - update
    - renew
    - delete (if you choose to unify it)

    Attributes:
        ok: Indicates success or failure
        status_code: HTTP status code returned by Oura API
        result: Parsed JSON payload (on success)
        error: Error detail (string or dict) on failure
    """

    ok: bool
    status_code: int
    result: Optional[dict[str, Any]] = None
    error: Optional[Any] = None

    # ----------------------------------------------------------
    # Convenience
    # ----------------------------------------------------------

    def __bool__(self) -> bool:
        return self.ok

    @property
    def is_success(self) -> bool:
        return self.ok

    @property
    def is_error(self) -> bool:
        return not self.ok

    def __repr__(self) -> str:
        return (
            f"WebhookSubscriptionResult("
            f"ok={self.ok}, "
            f"status_code={self.status_code}, "
            f"result_keys={list(self.result.keys()) if self.result else None}, "
            f"error={self.error})"
        )
