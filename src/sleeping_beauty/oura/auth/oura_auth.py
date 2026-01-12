from __future__ import annotations

import secrets
import webbrowser
from datetime import datetime, timezone
from typing import Iterable
from urllib.parse import urlencode

from sleeping_beauty.config.config import Config
from sleeping_beauty.oura.auth.domain.auth_preflight_result import AuthPreflightReport
from sleeping_beauty.oura.auth.domain.scopes import OURA_SCOPE_ALIASES

from .callback_server import OAuthCallbackServer
from .domain.exceptions import (
    AuthConfigurationError,
    AuthStorageError,
    CallbackValidationError,
    LoginRequiredError,
    OAuthTokenRefreshError,
    UserDeniedConsentError,
)
from .domain.token import TokenSet
from .oauth_http import (
    OURA_AUTHORIZE_URL,
    exchange_code_for_tokens,
    refresh_access_token,
    revoke_access_token,
)
from .storage.file_storage import FileTokenStorage


class OuraAuth:
    """
    Orchestrates the full OAuth lifecycle for Oura.

    This is the ONLY class that:
    - launches a browser
    - runs a callback server
    - decides between login vs refresh
    """

    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        scopes: Iterable[str],
        token_storage: FileTokenStorage,
        callback_host: str = "localhost",
        callback_port: int = 8400,
        callback_path: str = "/callback",
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._redirect_uri = redirect_uri
        self._scopes = self._normalize_scopes(set(scopes))

        self._storage = token_storage

        self._callback_host = callback_host
        self._callback_port = callback_port
        self._callback_path = callback_path

        self._validate_config()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    @classmethod
    def from_config(cls, config: Config | None = None) -> "OuraAuth":
        """
        Construct OuraAuth from application Config.

        This is the canonical construction path for:
        - CLI
        - notebooks
        - integration tests
        """
        cfg = config or Config()

        token_storage = FileTokenStorage(cfg.oura_token_path)

        return cls(
            client_id=cfg.oura_client_id,
            client_secret=cfg.oura_client_secret,
            redirect_uri=cfg.oura_redirect_uri,
            scopes=cfg.oura_scopes,
            token_storage=token_storage,
        )

    def preflight_check(self) -> AuthPreflightReport:
        """
        Perform a non-destructive preflight check of Oura OAuth configuration
        and current token state.

        Returns a PreflightResult containing:
        - ok: whether the setup appears usable
        - messages: human-readable diagnostic lines
        """
        ok = True
        messages: list[str] = []

        def add(msg: str):
            messages.append(msg)

        add("🔐 Oura Auth Preflight Check")
        add("-" * 40)

        # --- Config checks ---
        if not self._client_id:
            add("❌ Missing client_id")
            ok = False
        else:
            add("✅ client_id present")

        if not self._client_secret:
            add("❌ Missing client_secret")
            ok = False
        else:
            add("✅ client_secret present")

        if not self._redirect_uri:
            add("❌ Missing redirect_uri")
            ok = False
        else:
            add(f"✅ redirect_uri: {self._redirect_uri}")

        if not self._scopes:
            add("❌ No scopes configured")
            ok = False
        else:
            add(f"✅ requested scopes: {sorted(self._scopes)}")

        # --- Token checks ---
        token = self._storage.load()
        if not token:
            add("⚠️  No stored token found (OAuth flow will be required)")
            add("-" * 40)
            add("✔️  Preflight check complete")
            return AuthPreflightReport(ok=ok, messages=messages)

        add("✅ token found in storage")

        expires_at = getattr(token, "expires_at", None)
        if expires_at:
            expiry = datetime.fromtimestamp(expires_at, tz=timezone.utc)
            now = datetime.now(tz=timezone.utc)

            if expiry <= now:
                add("❌ token is expired")
                ok = False
            else:
                remaining = int((expiry - now).total_seconds() // 60)
                add(f"✅ token valid for ~{remaining} minutes")
        else:
            add("⚠️  token has no expires_at field")

        # --- Scope coverage ---
        token_scopes_raw = getattr(token, "scope", None)
        if token_scopes_raw:
            token_scopes = set(token_scopes_raw.split())
            missing = self._scopes - token_scopes
            if missing:
                add(f"⚠️  token missing scopes: {sorted(missing)}")
            else:
                add("✅ token covers requested scopes")
        else:
            add("⚠️  token has no scope information")

        add("-" * 40)
        add("✔️  Preflight check complete")

        return AuthPreflightReport(ok=ok, messages=messages)

    def get_access_token(self) -> str:
        """
        Return a valid access token.

        - refreshes if expired / near-expiry
        - raises LoginRequiredError if interactive login is required
        """
        token = self._load_token()

        if token is None:
            raise LoginRequiredError("No stored OAuth token")

        if not token.has_scopes(self._scopes):
            raise LoginRequiredError("Stored token does not satisfy required scopes")

        if token.requires_refresh():
            token = self._refresh_token(token)
            self._storage.save(token)

        return token.access_token

    def login_interactive(self) -> None:
        """
        Perform a full browser-based OAuth login.
        """
        state = self._generate_state()

        server = OAuthCallbackServer(
            host=self._callback_host,
            port=self._callback_port,
            expected_path=self._callback_path,
            expected_state=state,
        )

        auth_url = self._build_authorization_url(state)
        webbrowser.open(auth_url)

        try:
            result = server.wait_for_callback()
        except UserDeniedConsentError:
            raise
        except CallbackValidationError:
            raise

        token = exchange_code_for_tokens(
            client_id=self._client_id,
            client_secret=self._client_secret,
            code=result.code,
            redirect_uri=self._redirect_uri,
        )

        self._storage.save(token)

    def revoke(self) -> None:
        """
        Best-effort revocation + local token removal.
        """
        token = self._load_token()
        if token:
            try:
                revoke_access_token(access_token=token.access_token)
            finally:
                self._storage.clear()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _refresh_token(self, token: TokenSet) -> TokenSet:
        """
        Refresh an access token, handling rotation semantics.
        """
        try:
            return refresh_access_token(
                client_id=self._client_id,
                client_secret=self._client_secret,
                refresh_token=token.refresh_token,
            )
        except OAuthTokenRefreshError:
            # Refresh token invalid / rotated / revoked
            raise LoginRequiredError("Refresh token invalid; login required")

    def _load_token(self) -> TokenSet | None:
        try:
            return self._storage.load()
        except AuthStorageError:
            raise

    def _build_authorization_url(self, state: str) -> str:
        scope = " ".join(sorted(self._scopes))

        auth_params = {
            "client_id": self._client_id,
            "redirect_uri": self._redirect_uri,
            "response_type": "code",
            "scope": scope,
            "state": state,
        }
        auth_url = (
            f"https://cloud.ouraring.com/oauth/authorize?{urlencode(auth_params)}"
        )
        return auth_url

    def _generate_state(self) -> str:
        return secrets.token_urlsafe(32)

    def _validate_config(self) -> None:
        if not self._client_id:
            raise AuthConfigurationError("Missing client_id")

        if not self._client_secret:
            raise AuthConfigurationError("Missing client_secret")

        if not self._redirect_uri:
            raise AuthConfigurationError("Missing redirect_uri")

        if not self._scopes:
            raise AuthConfigurationError("No OAuth scopes configured")

    def _normalize_scopes(self, scopes: set[str]) -> set[str]:
        normalized: set[str] = set()

        for scope in scopes:
            if scope.startswith("extapi:"):
                normalized.add(scope)
            else:
                try:
                    normalized.add(OURA_SCOPE_ALIASES[scope])
                except KeyError:
                    raise AuthConfigurationError(f"Unknown Oura scope: {scope}")

        return normalized
