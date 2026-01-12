from __future__ import annotations

from pathlib import Path
from typing import Iterable

from sleeping_beauty.config.config import Config
from sleeping_beauty.logsys.logger_manager import LoggerManager
from sleeping_beauty.oura.auth.domain.exceptions import (
    AuthConfigurationError,
    LoginRequiredError,
)
from sleeping_beauty.oura.auth.oura_auth import OuraAuth
from sleeping_beauty.oura.auth.storage.file_storage import FileTokenStorage

logger = LoggerManager.get_logger(__name__)


class AuthService:
    """
    Application service for Oura authentication use cases.

    This class encapsulates *what* the application can do with authentication,
    independent of CLI, async runtime, or orchestration concerns.

    Supported use cases:
      - login
      - status
      - revoke
    """

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(
        self,
        *,
        redirect_uri: str | None = None,
        scopes: Iterable[str] | None = None,
    ) -> None:
        self.config = Config()

        if not self.config.oura_client_id:
            logger.error("Missing OURA_CLIENT_ID (env or config)")
            raise AuthConfigurationError("Missing OURA_CLIENT_ID")

        if not self.config.oura_client_secret:
            logger.error("Missing OURA_CLIENT_SECRET (env or config)")
            raise AuthConfigurationError("Missing OURA_CLIENT_SECRET")

        logger.debug("Initializing AuthService")

        self._storage = FileTokenStorage(
            path=Path(self.config.oura_token_path).expanduser()
        )

        self._auth = OuraAuth(
            client_id=self.config.oura_client_id,
            client_secret=self.config.oura_client_secret,
            redirect_uri=self.config.oura_redirect_uri,
            scopes=self.config.oura_scopes,
            token_storage=self._storage,
        )

    # ------------------------------------------------------------------
    # Use cases
    # ------------------------------------------------------------------

    def login(self) -> None:
        """
        Run interactive OAuth login.
        """
        logger.info("Starting interactive Oura login flow")
        self._auth.login_interactive()
        logger.info("Login successful")

    def status(self) -> None:
        """
        Log authentication status.
        """
        logger.debug("Checking authentication status")

        try:
            token = self._auth.get_access_token()
            logger.info("Authenticated successfully")
            logger.debug("Access token present (length=%d)", len(token))
        except LoginRequiredError:
            logger.warning("Not authenticated – login required")

    def revoke(self) -> None:
        """
        Revoke access token and clear local storage.
        """
        logger.info("Revoking Oura access token")
        self._auth.revoke()
        logger.info("Token revoked and local storage cleared")

    # ------------------------------------------------------------------
    # Dispatch helper (CLI-friendly, but not CLI-specific)
    # ------------------------------------------------------------------

    def run(self, command: str) -> None:
        """
        Dispatch an auth command.

        Intended for thin callers (CLI, host, automation).
        """
        logger.debug("AuthService dispatch command={}", command)

        if command == "login":
            self.login()
        elif command == "status":
            self.status()
        elif command == "revoke":
            self.revoke()
        else:
            logger.error("Unknown auth command: {}", command)
            raise ValueError(f"Unknown auth command: {command}")
