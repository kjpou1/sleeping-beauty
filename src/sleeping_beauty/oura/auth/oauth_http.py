from __future__ import annotations

import time
from typing import Any

import httpx

from .domain.exceptions import (
    AuthNetworkError,
    OAuthAuthorizationError,
    OAuthRevocationError,
    OAuthTokenExchangeError,
    OAuthTokenRefreshError,
)
from .domain.token import InvalidTokenError, TokenSet

# Oura OAuth endpoints (v2)
OURA_AUTHORIZE_URL = "https://cloud.ouraring.com/oauth/authorize"
OURA_TOKEN_URL = "https://api.ouraring.com/oauth/token"
OURA_REVOKE_URL = "https://api.ouraring.com/oauth/revoke"


# ---------- Public functions ----------


def exchange_code_for_tokens(
    *,
    client_id: str,
    client_secret: str,
    code: str,
    redirect_uri: str,
    timeout_seconds: float = 20.0,
    http: httpx.Client | None = None,
) -> TokenSet:
    """
    Exchange an authorization code for an access+refresh TokenSet.
    """
    if not code:
        raise OAuthTokenExchangeError(
            error="invalid_request", description="Missing authorization code"
        )

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
    }

    return _token_request(
        data=data,
        client_id=client_id,
        client_secret=client_secret,
        timeout_seconds=timeout_seconds,
        http=http,
        on_oauth_error=OAuthTokenExchangeError,
    )


def refresh_access_token(
    *,
    client_id: str,
    client_secret: str,
    refresh_token: str,
    timeout_seconds: float = 20.0,
    http: httpx.Client | None = None,
) -> TokenSet:
    """
    Refresh an access token using a refresh token.

    Note: Oura refresh tokens are single-use (rotating). The returned TokenSet
    will contain a NEW refresh_token that must be persisted atomically.
    """
    if not refresh_token:
        raise OAuthTokenRefreshError(
            error="invalid_request", description="Missing refresh_token"
        )

    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }

    return _token_request(
        data=data,
        client_id=client_id,
        client_secret=client_secret,
        timeout_seconds=timeout_seconds,
        http=http,
        on_oauth_error=OAuthTokenRefreshError,
    )


def revoke_access_token(
    *,
    access_token: str,
    timeout_seconds: float = 20.0,
    http: httpx.Client | None = None,
) -> None:
    """
    Best-effort token revocation.

    Oura's docs show a revoke endpoint that takes access_token as a query param.
    We treat non-2xx responses as revocation failures (but caller may choose to ignore).
    """
    if not access_token:
        raise OAuthRevocationError(
            error="invalid_request", description="Missing access_token"
        )

    params = {"access_token": access_token}

    client = http or httpx.Client(timeout=timeout_seconds)
    owns_client = http is None

    try:
        resp = client.post(OURA_REVOKE_URL, params=params)
    except httpx.RequestError as exc:
        raise AuthNetworkError(f"Network error calling revoke endpoint: {exc}") from exc
    finally:
        if owns_client:
            client.close()

    if 200 <= resp.status_code < 300:
        return

    # Try to parse an OAuth-style error body; if not available, include text
    err, desc, raw = _extract_oauth_error(resp)
    raise OAuthRevocationError(
        error=err or "revocation_failed",
        description=desc or _safe_body_snippet(resp),
        status_code=resp.status_code,
        raw=raw,
    )


# ---------- Internal helpers ----------


def _token_request(
    *,
    data: dict[str, str],
    client_id: str,
    client_secret: str,
    timeout_seconds: float,
    http: httpx.Client | None,
    on_oauth_error: type[OAuthTokenExchangeError] | type[OAuthTokenRefreshError],
) -> TokenSet:
    """
    Execute a POST to the token endpoint using application/x-www-form-urlencoded
    and HTTP Basic auth.

    on_oauth_error controls which OAuthError subclass we raise for protocol failures.
    """
    if not client_id or not client_secret:
        # This is technically a configuration problem, but we keep oauth_http focused:
        # token exchange cannot proceed without credentials.
        raise on_oauth_error(
            error="invalid_client", description="Missing client_id/client_secret"
        )

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    }

    auth = (client_id, client_secret)

    client = http or httpx.Client(timeout=timeout_seconds)
    owns_client = http is None

    try:
        resp = client.post(OURA_TOKEN_URL, data=data, headers=headers, auth=auth)
    except httpx.RequestError as exc:
        raise AuthNetworkError(f"Network error calling token endpoint: {exc}") from exc
    finally:
        if owns_client:
            client.close()

    if 200 <= resp.status_code < 300:
        try:
            payload = resp.json()
        except Exception as exc:
            raise on_oauth_error(
                error="invalid_response",
                description="Token endpoint returned non-JSON response",
                status_code=resp.status_code,
                raw={"text": _safe_body_snippet(resp)},
            ) from exc

        try:
            return _token_set_from_payload(payload)
        except (KeyError, TypeError, ValueError, InvalidTokenError) as exc:
            raise on_oauth_error(
                error="invalid_response",
                description="Token endpoint JSON did not contain a valid token set",
                status_code=resp.status_code,
                raw=_safe_payload(payload),
            ) from exc

    # Non-2xx => OAuth-ish error
    err, desc, raw = _extract_oauth_error(resp)
    raise on_oauth_error(
        error=err or "token_request_failed",
        description=desc or _safe_body_snippet(resp),
        status_code=resp.status_code,
        raw=raw,
    )


def _token_set_from_payload(payload: dict[str, Any]) -> TokenSet:
    """
    Convert a token endpoint JSON payload into a TokenSet.

    Expected fields from Oura (per docs):
    - access_token
    - refresh_token
    - expires_in
    - token_type
    - scope
    """
    now = int(time.time())

    expires_in = int(payload["expires_in"])
    expires_at = now + expires_in

    return TokenSet(
        access_token=str(payload["access_token"]),
        refresh_token=str(payload["refresh_token"]),
        expires_at=expires_at,
        scope=str(payload["scope"]),
        token_type=str(payload.get("token_type", "bearer")),
        obtained_at=now,
    )


def _extract_oauth_error(
    resp: httpx.Response,
) -> tuple[str | None, str | None, dict[str, Any]]:
    """
    Attempt to extract OAuth-style error details from a response body.

    Many OAuth servers return:
      {"error": "...", "error_description": "..."}
    """
    try:
        payload = resp.json()
    except Exception:
        return None, None, {"text": _safe_body_snippet(resp)}

    if isinstance(payload, dict):
        err = payload.get("error")
        desc = payload.get("error_description") or payload.get(
            "error_description".replace("_", " ")
        )
        # (Keep raw payload for debugging, but sanitized by caller if needed)
        return (
            str(err) if err else None,
            str(desc) if desc else None,
            _safe_payload(payload),
        )

    return None, None, {"text": _safe_body_snippet(resp)}


def _safe_body_snippet(resp: httpx.Response, *, limit: int = 500) -> str:
    """
    Return a bounded snippet of the response text for debugging.
    """
    try:
        text = resp.text
    except Exception:
        return "<unreadable response body>"
    return text[:limit]


def _safe_payload(payload: dict[str, Any], *, limit_keys: int = 50) -> dict[str, Any]:
    """
    Keep payload reasonably sized for exception.raw.
    NOTE: This does not redact secrets. Callers should avoid logging raw payloads
    in plaintext in production.
    """
    if len(payload) <= limit_keys:
        return payload
    # Truncate large dicts deterministically
    out: dict[str, Any] = {}
    for i, k in enumerate(sorted(payload.keys())):
        if i >= limit_keys:
            out["__truncated__"] = True
            out["__total_keys__"] = len(payload)
            break
        out[k] = payload[k]
    return out
