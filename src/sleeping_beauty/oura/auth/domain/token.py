from __future__ import annotations

import time
from dataclasses import dataclass, field


class InvalidTokenError(ValueError):
    """
    Raised when a TokenSet is constructed with invalid or inconsistent data.
    This is a programmer / data integrity error, not an OAuth protocol error.
    """

    pass


@dataclass(frozen=True, slots=True)
class TokenSet:
    """
    Represents a complete OAuth token set issued by Oura.

    This object is intentionally immutable. Token refresh MUST produce
    a new TokenSet instance to avoid subtle state bugs.
    """

    access_token: str
    refresh_token: str
    expires_at: int
    scope: str
    token_type: str = "bearer"
    obtained_at: int = field(default_factory=lambda: int(time.time()))

    def __post_init__(self) -> None:
        # Basic presence checks
        if not self.access_token:
            raise InvalidTokenError("access_token must be non-empty")

        if not self.refresh_token:
            raise InvalidTokenError("refresh_token must be non-empty")

        if not isinstance(self.expires_at, int) or self.expires_at <= 0:
            raise InvalidTokenError("expires_at must be a positive unix timestamp")

        if not self.scope:
            raise InvalidTokenError("scope must be non-empty")

        if self.expires_at <= self.obtained_at:
            raise InvalidTokenError("expires_at must be later than obtained_at")

    # ---- Time / validity helpers ----

    def expires_in(self, *, now: int | None = None) -> int:
        """
        Returns seconds until expiry (can be negative if already expired).
        """
        current = now if now is not None else int(time.time())
        return self.expires_at - current

    def is_expired(self, *, skew_seconds: int = 60, now: int | None = None) -> bool:
        """
        Returns True if the token should be considered expired.

        skew_seconds accounts for:
        - clock drift
        - network latency
        - request execution time
        """
        return self.expires_in(now=now) <= skew_seconds

    def requires_refresh(
        self, *, skew_seconds: int = 300, now: int | None = None
    ) -> bool:
        """
        Returns True if the token is approaching expiry and should be refreshed.
        """
        return self.expires_in(now=now) <= skew_seconds

    # ---- Scope helpers ----

    def scope_set(self) -> set[str]:
        """
        Returns scopes as a normalized set.
        """
        return set(self.scope.split())

    def has_scopes(self, required: set[str]) -> bool:
        """
        Returns True if all required scopes are present.
        """
        return required.issubset(self.scope_set())
