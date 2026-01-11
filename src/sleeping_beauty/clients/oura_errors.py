from __future__ import annotations


class OuraApiError(Exception):
    """
    Base exception for all Oura API errors.
    """

    def __init__(
        self,
        *,
        status_code: int,
        message: str,
        response: dict | None = None,
        request_id: str | None = None,
    ) -> None:
        self.status_code = status_code
        self.message = message
        self.response = response
        self.request_id = request_id

        super().__init__(f"[{status_code}] {message}")


# ---------------------------------------------------------------------
# 4xx – Client errors
# ---------------------------------------------------------------------


class OuraClientError(OuraApiError):
    """Generic 4xx client error."""


class OuraBadRequestError(OuraClientError):
    """400 – Invalid request parameters."""


class OuraAuthError(OuraClientError):
    """401 – Invalid or expired access token."""


class OuraForbiddenError(OuraClientError):
    """403 – Missing required OAuth scope."""


class OuraNotFoundError(OuraClientError):
    """404 – Endpoint or resource not found."""


class OuraConflictError(OuraClientError):
    """409 – Conflict."""


# ---------------------------------------------------------------------
# 429 – Rate limiting
# ---------------------------------------------------------------------


class OuraRateLimitError(OuraApiError):
    """429 – Rate limit exceeded."""


# ---------------------------------------------------------------------
# 5xx – Server errors
# ---------------------------------------------------------------------


class OuraServerError(OuraApiError):
    """5xx – Oura internal server error."""
