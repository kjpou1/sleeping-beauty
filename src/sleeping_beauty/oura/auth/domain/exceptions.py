from __future__ import annotations

# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------


class AuthError(Exception):
    """
    Base class for all authentication-related errors.

    Anything raised by the auth subsystem MUST derive from this type,
    except for programmer errors (ValueError, TypeError, etc.).
    """

    pass


# ---------------------------------------------------------------------------
# Configuration / environment errors (fatal)
# ---------------------------------------------------------------------------


class AuthConfigurationError(AuthError):
    """
    Invalid or missing OAuth configuration.

    Examples:
    - missing client_id / client_secret
    - invalid redirect_uri
    - unsupported scope configuration
    """

    pass


class AuthStorageError(AuthError):
    """
    Failure loading, parsing, or persisting token data.

    Indicates local environment or filesystem problems.
    """

    pass


# ---------------------------------------------------------------------------
# Network / transport errors (retryable)
# ---------------------------------------------------------------------------


class AuthNetworkError(AuthError):
    """
    Network-level failure communicating with Oura.

    Examples:
    - DNS failure
    - connection timeout
    - connection reset
    """

    pass


# ---------------------------------------------------------------------------
# OAuth protocol errors (remote / structured)
# ---------------------------------------------------------------------------


class OAuthError(AuthError):
    """
    Base class for OAuth protocol errors returned by Oura.

    Carries structured information so callers can log or inspect
    the exact failure.
    """

    def __init__(
        self,
        *,
        error: str,
        description: str | None = None,
        status_code: int | None = None,
        raw: dict | None = None,
    ) -> None:
        self.error = error
        self.description = description
        self.status_code = status_code
        self.raw = raw or {}

        super().__init__(self._format_message())

    def _format_message(self) -> str:
        msg = f"OAuth error: {self.error}"
        if self.description:
            msg += f" – {self.description}"
        if self.status_code is not None:
            msg += f" (HTTP {self.status_code})"
        return msg


class OAuthAuthorizationError(OAuthError):
    """
    Error during the authorization (user consent) step.
    """

    pass


class OAuthTokenExchangeError(OAuthError):
    """
    Error exchanging an authorization code for tokens.
    """

    pass


class OAuthTokenRefreshError(OAuthError):
    """
    Error refreshing an access token.

    Common causes:
    - refresh token already used (rotation)
    - refresh token revoked
    - refresh token expired
    """

    pass


class OAuthRevocationError(OAuthError):
    """
    Error revoking an access token.
    """

    pass


# --------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Control-flow / expected signals (not bugs)
# ---------------------------------------------------------------------------


class LoginRequiredError(AuthError):
    """
    No valid tokens available; interactive login is required.

    This is a control signal, not a failure.
    """

    pass


class UserDeniedConsentError(AuthError):
    """
    User explicitly denied OAuth consent (error=access_denied).
    """

    pass


class CallbackValidationError(AuthError):
    """
    Invalid OAuth callback received.

    Examples:
    - state mismatch
    - missing code and error
    - malformed parameters
    """

    pass
