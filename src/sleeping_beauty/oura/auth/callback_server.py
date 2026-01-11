from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

from .domain.exceptions import CallbackValidationError, UserDeniedConsentError


class OAuthCallbackResult:
    """
    Simple container for the OAuth callback outcome.
    """

    def __init__(self, *, code: str) -> None:
        self.code = code


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """
    HTTP handler for the OAuth redirect.

    Communicates result back to the server via shared state.
    """

    server: "OAuthCallbackServer"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        try:
            oauth_server = self.server.oauth_server
            oauth_server._handle_callback(parsed.path, params)
            self._send_success_response()
        except UserDeniedConsentError:
            self._send_user_denied_response()
        except CallbackValidationError as exc:
            self._send_error_response(str(exc))
        finally:
            # Ensure the server stops after handling one request
            threading.Thread(target=self.server.shutdown, daemon=True).start()

    def log_message(self, format: str, *args) -> None:
        # Silence default HTTP logging
        return

    def _send_success_response(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(
            b"<html><body><h2>Authentication complete.</h2>"
            b"<p>You may close this tab.</p></body></html>"
        )

    def _send_user_denied_response(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(
            b"<html><body><h2>Authentication cancelled.</h2>"
            b"<p>You may close this tab.</p></body></html>"
        )

    def _send_error_response(self, message: str) -> None:
        self.send_response(400)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(
            f"<html><body><h2>Authentication error.</h2>"
            f"<p>{message}</p></body></html>".encode("utf-8")
        )


class OAuthCallbackServer:
    """
    Local HTTP server that waits for a single OAuth redirect.

    Usage:
        server = OAuthCallbackServer(
            host="127.0.0.1",
            port=8400,
            expected_path="/callback",
            expected_state=state,
        )
        result = server.wait_for_callback()
        code = result.code
    """

    def __init__(
        self,
        *,
        host: str,
        port: int,
        expected_path: str,
        expected_state: str,
    ) -> None:
        self._expected_path = expected_path
        self._expected_state = expected_state

        self._result: OAuthCallbackResult | None = None
        self._error: Exception | None = None

        self._httpd = HTTPServer((host, port), OAuthCallbackHandler)
        # Attach back-reference explicitly
        self._httpd.oauth_server = self

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def wait_for_callback(self) -> OAuthCallbackResult:
        """
        Block until the OAuth redirect is received and processed.

        Raises:
            UserDeniedConsentError
            CallbackValidationError
        """
        try:
            self._httpd.serve_forever()
        finally:
            self._httpd.server_close()

        if self._error:
            raise self._error

        if not self._result:
            raise CallbackValidationError("No OAuth callback received")

        return self._result

    def shutdown(self) -> None:
        self._httpd.shutdown()

    # ------------------------------------------------------------------
    # Internal logic
    # ------------------------------------------------------------------

    def _handle_callback(self, path: str, params: dict[str, list[str]]) -> None:
        # Path must match exactly
        if path != self._expected_path:
            self._error = CallbackValidationError(f"Unexpected callback path: {path}")
            raise self._error

        # State must be present and correct
        state = _get_single_param(params, "state")
        if state != self._expected_state:
            self._error = CallbackValidationError("OAuth state mismatch")
            raise self._error

        # User explicitly denied consent
        if "error" in params:
            error = _get_single_param(params, "error")
            if error == "access_denied":
                self._error = UserDeniedConsentError("User denied OAuth consent")
                raise self._error
            self._error = CallbackValidationError(f"OAuth error: {error}")
            raise self._error

        # Success case: authorization code
        code = _get_single_param(params, "code")
        if not code:
            self._error = CallbackValidationError("Missing authorization code")
            raise self._error

        self._result = OAuthCallbackResult(code=code)


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


def _get_single_param(params: dict[str, list[str]], name: str) -> str | None:
    values = params.get(name)
    if not values:
        return None
    if len(values) != 1:
        raise CallbackValidationError(f"Multiple values for parameter '{name}'")
    return values[0]
