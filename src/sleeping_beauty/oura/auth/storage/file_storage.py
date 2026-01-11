from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from ..domain.exceptions import AuthStorageError
from ..domain.token import InvalidTokenError, TokenSet


class FileTokenStorage:
    """
    File-based storage for OAuth tokens.

    Guarantees:
    - atomic writes
    - crash-safe refresh token rotation
    - explicit failure on corruption
    """

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(self) -> TokenSet | None:
        """
        Load the token set from disk.

        Returns None if the token file does not exist.
        Raises AuthStorageError if the file exists but is invalid.
        """
        if not self._path.exists():
            return None

        try:
            with self._path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as exc:
            raise AuthStorageError(f"Failed to read token file: {self._path}") from exc

        try:
            return self._parse_token_data(data)
        except (KeyError, TypeError, ValueError, InvalidTokenError) as exc:
            raise AuthStorageError(
                f"Token file is corrupted or invalid: {self._path}"
            ) from exc

    def save(self, token: TokenSet) -> None:
        """
        Persist a token set atomically.

        Uses write-then-rename to guarantee atomic replacement.
        """
        payload = self._serialize_token(token)

        self._path.parent.mkdir(parents=True, exist_ok=True)

        try:
            self._atomic_write(payload)
        except Exception as exc:
            raise AuthStorageError(
                f"Failed to persist token file: {self._path}"
            ) from exc

    def clear(self) -> None:
        """
        Remove the token file if it exists.
        """
        try:
            if self._path.exists():
                self._path.unlink()
        except Exception as exc:
            raise AuthStorageError(
                f"Failed to remove token file: {self._path}"
            ) from exc

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _parse_token_data(self, data: dict[str, Any]) -> TokenSet:
        """
        Validate and construct a TokenSet from raw JSON data.
        """
        return TokenSet(
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            expires_at=int(data["expires_at"]),
            scope=data["scope"],
            token_type=data.get("token_type", "bearer"),
            obtained_at=int(data.get("obtained_at", data["expires_at"])),
        )

    def _serialize_token(self, token: TokenSet) -> dict[str, Any]:
        """
        Convert a TokenSet into a JSON-serializable dict.
        """
        return {
            "access_token": token.access_token,
            "refresh_token": token.refresh_token,
            "expires_at": token.expires_at,
            "scope": token.scope,
            "token_type": token.token_type,
            "obtained_at": token.obtained_at,
        }

    def _atomic_write(self, payload: dict[str, Any]) -> None:
        """
        Write JSON payload atomically to the target path.
        """
        directory = self._path.parent

        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=directory,
            delete=False,
        ) as tmp:
            json.dump(payload, tmp, indent=2)
            tmp.flush()
            os.fsync(tmp.fileno())
            temp_name = tmp.name

        os.replace(temp_name, self._path)
