from __future__ import annotations

import asyncio
from datetime import date
from typing import Callable, Iterable, NoReturn, Optional

import httpx

from sleeping_beauty.clients.oura_endpoints import session as session_endpoints
from sleeping_beauty.clients.oura_endpoints.daily_sleep_score import (
    parse_daily_sleep_score_item,
    parse_daily_sleep_score_page,
)
from sleeping_beauty.clients.oura_endpoints.heartrate import parse_heartrate_page
from sleeping_beauty.clients.oura_endpoints.personal_info import parse_personal_info
from sleeping_beauty.clients.oura_endpoints.sleep import (
    parse_sleep_document,
    parse_sleep_document_page,
)
from sleeping_beauty.clients.oura_errors import (
    OuraApiError,
    OuraAuthError,
    OuraBadRequestError,
    OuraClientError,
    OuraConflictError,
    OuraForbiddenError,
    OuraNotFoundError,
    OuraRateLimitError,
    OuraServerError,
)
from sleeping_beauty.models.oura.daily_sleep_score import DailySleepScore
from sleeping_beauty.models.oura.heartrate import HeartRateSample
from sleeping_beauty.models.oura.page import Page
from sleeping_beauty.models.oura.personal_info import PersonalInfo
from sleeping_beauty.models.oura.session import Session
from sleeping_beauty.models.oura.sleep import SleepDocument

TokenProvider = Callable[[], str]


class OuraApiClient:
    """
    Async-first Oura API v2 client.

    Sync methods (suffix `_sync`) are thin wrappers around async methods
    and will fail fast if called from a running event loop.
    """

    def __init__(
        self,
        *,
        token_provider: TokenProvider,
        base_url: str = "https://api.ouraring.com",
        timeout_s: float = 30.0,
        user_agent: str = "sleeping-beauty/0.1",
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._token_provider = token_provider

        if not callable(token_provider):
            raise TypeError(
                "token_provider must be a callable returning an access token, "
                "not a token value"
            )

        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_s

        self._client: httpx.AsyncClient = client or httpx.AsyncClient(
            base_url=self._base_url,
            timeout=self._timeout,
            headers={
                "User-Agent": user_agent,
                "Accept": "application/json",
            },
        )

        self._owns_client = client is None

    # ---------------------------------------------------------------------
    # Sync boundary
    # ---------------------------------------------------------------------

    def _run(self, coro):
        """
        Explicit sync boundary.

        This will raise if called while an event loop is already running.
        """
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)
        else:
            raise RuntimeError(
                "Sync API called while an event loop is running. "
                "Use the async API instead."
            )

    # ---------------------------------------------------------------------
    # HTTP transport (async, canonical)
    # ---------------------------------------------------------------------

    async def _request_async(
        self,
        *,
        method: str,
        path: str,
        params: dict | None = None,
    ) -> dict:
        """
        Execute a single HTTP request against the Oura API.

        Raises typed OuraApiError subclasses on failure.
        """
        headers = {
            "Authorization": f"Bearer {self._token_provider()}",
        }

        response = await self._client.request(
            method=method,
            url=path,
            params=params,
            headers=headers,
        )

        payload: dict | None
        try:
            payload = response.json()
        except ValueError:
            payload = None

        if response.status_code >= 400:
            self._raise_for_status(
                status_code=response.status_code,
                payload=payload,
                headers=response.headers,
            )

        return payload or {}

    # ---------------------------------------------------------------------
    # Error mapping
    # ---------------------------------------------------------------------

    def _raise_for_status(
        self,
        *,
        status_code: int,
        payload: dict | None,
        headers: httpx.Headers,
    ) -> NoReturn:
        message = (
            (payload.get("error") or payload.get("message") or "Oura API error")
            if payload
            else "Oura API error"
        )

        request_id = headers.get("x-request-id")

        if status_code == 400:
            raise OuraBadRequestError(
                status_code=status_code,
                message=message,
                response=payload,
                request_id=request_id,
            )

        if status_code == 401:
            raise OuraAuthError(
                status_code=status_code,
                message=message,
                response=payload,
                request_id=request_id,
            )

        if status_code == 403:
            raise OuraForbiddenError(
                status_code=status_code,
                message=message,
                response=payload,
                request_id=request_id,
            )

        if status_code == 404:
            raise OuraNotFoundError(
                status_code=status_code,
                message=message,
                response=payload,
                request_id=request_id,
            )

        if status_code == 409:
            raise OuraConflictError(
                status_code=status_code,
                message=message,
                response=payload,
                request_id=request_id,
            )

        if status_code == 429:
            raise OuraRateLimitError(
                status_code=status_code,
                message=message,
                response=payload,
                request_id=request_id,
            )

        if 400 <= status_code < 500:
            raise OuraClientError(
                status_code=status_code,
                message=message,
                response=payload,
                request_id=request_id,
            )

        if status_code >= 500:
            raise OuraServerError(
                status_code=status_code,
                message=message,
                response=payload,
                request_id=request_id,
            )

        raise OuraApiError(
            status_code=status_code,
            message=message,
            response=payload,
            request_id=request_id,
        )

    # ---------------------------------------------------------------------
    # Lifecycle
    # ---------------------------------------------------------------------

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> "OuraApiClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.aclose()

    ###########
    #
    # Public facing api implementations
    #
    ###########

    # ---------------------------------------------------------------------
    # Public API — Personal Info
    # ---------------------------------------------------------------------

    async def get_personal_info(self) -> PersonalInfo:
        """
        Fetch the user's personal information.

        GET /v2/usercollection/personal_info
        """
        payload = await self._request_async(
            method="GET",
            path="/v2/usercollection/personal_info",
        )

        return parse_personal_info(payload)

    def get_personal_info_sync(self) -> PersonalInfo:
        """
        Synchronous wrapper around get_personal_info().
        """
        return self._run(self.get_personal_info())

    # ---------------------------------------------------------------------
    # Public API — Daily Sleep Scores
    # ---------------------------------------------------------------------

    async def get_daily_sleep_score_page(
        self,
        *,
        start_date: date,
        end_date: date,
        next_token: str | None = None,
    ) -> Page[DailySleepScore]:
        """
        Fetch one page of daily sleep score summaries.

        GET /v2/usercollection/daily_sleep
        """
        params: dict[str, str] = {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        }
        if next_token:
            params["next_token"] = next_token

        payload = await self._request_async(
            method="GET",
            path="/v2/usercollection/daily_sleep",
            params=params,
        )

        return parse_daily_sleep_score_page(payload)

    async def iter_daily_sleep_scores(
        self,
        *,
        start_date: date,
        end_date: date,
    ):
        """
        Iterate over all DailySleepScore records in the given date range.
        """
        token: str | None = None

        while True:
            page = await self.get_daily_sleep_score_page(
                start_date=start_date,
                end_date=end_date,
                next_token=token,
            )

            for item in page.data:
                yield item

            if not page.next_token:
                break

            token = page.next_token

    def get_daily_sleep_score_page_sync(
        self,
        *,
        start_date: date,
        end_date: date,
        next_token: str | None = None,
    ) -> Page[DailySleepScore]:
        """
        Synchronous wrapper around get_daily_sleep_score_page().
        """
        return self._run(
            self.get_daily_sleep_score_page(
                start_date=start_date,
                end_date=end_date,
                next_token=next_token,
            )
        )

    def iter_daily_sleep_scores_sync(
        self,
        *,
        start_date: date,
        end_date: date,
    ):
        """
        Synchronous wrapper around iter_daily_sleep_scores().
        """

        async def _collect():
            return [
                item
                async for item in self.iter_daily_sleep_scores(
                    start_date=start_date,
                    end_date=end_date,
                )
            ]

        return iter(self._run(_collect()))

    # ---------------------------------------------------------------------
    # Public API — Daily Sleep Scores (Single Document)
    # ---------------------------------------------------------------------

    async def get_daily_sleep_score(
        self,
        *,
        document_id: str,
    ) -> DailySleepScore:
        """
        Fetch a single daily sleep score document by ID.

        GET /v2/usercollection/daily_sleep/{document_id}
        """
        if not document_id:
            raise ValueError("document_id must be a non-empty string")

        payload = await self._request_async(
            method="GET",
            path=f"/v2/usercollection/daily_sleep/{document_id}",
            params=None,
        )

        # Single-document endpoint returns the document itself
        return parse_daily_sleep_score_item(payload)

    def get_daily_sleep_score_sync(
        self,
        *,
        document_id: str,
    ) -> DailySleepScore:
        """
        Synchronous wrapper around get_daily_sleep_score().
        """
        return self._run(self.get_daily_sleep_score(document_id=document_id))

    # ---------------------------------------------------------------------
    # Public API — Sessions (Multiple Document)
    # ---------------------------------------------------------------------
    async def get_sessions(
        self,
        *,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> Iterable[Session]:
        next_token = None
        while True:
            batch, next_token = await session_endpoints.get_sessions(
                self,
                start_date=start_date,
                end_date=end_date,
                next_token=next_token,
            )
            for item in batch:
                yield item
            if not next_token:
                break

    def get_sessions_sync(
        self,
        *,
        start_date: str | None = None,
        end_date: str | None = None,
    ):
        """
        Synchronous wrapper around get_sessions().
        """

        async def _collect():
            return [
                item
                async for item in self.get_sessions(
                    start_date=start_date,
                    end_date=end_date,
                )
            ]

        return iter(self._run(_collect()))

    # ---------------------------------------------------------------------
    # Public API — Session (Single Document)
    # ---------------------------------------------------------------------

    async def get_session(self, document_id: str) -> Session:
        return await session_endpoints.get_session(self, document_id)

    def get_session_sync(
        self,
        document_id: str,
    ) -> Session:
        """
        Synchronous wrapper around get_session().
        """
        return self._run(self.get_session(document_id))

    # ---------------------------------------------------------------------
    # Public API — Sleep Documents
    # ---------------------------------------------------------------------

    async def get_sleep_page(
        self,
        *,
        start_date: date,
        end_date: date,
        next_token: str | None = None,
    ) -> Page[SleepDocument]:
        """
        Fetch one page of sleep documents.

        GET /v2/usercollection/sleep
        """
        params: dict[str, str] = {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        }

        if next_token:
            params["next_token"] = next_token

        payload = await self._request_async(
            method="GET",
            path="/v2/usercollection/sleep",
            params=params,
        )

        return parse_sleep_document_page(payload)

    async def iter_sleep(
        self,
        *,
        start_date: date,
        end_date: date,
    ):
        """
        Iterate over all SleepDocument records in the given date range.
        """
        token: str | None = None

        while True:
            page = await self.get_sleep_page(
                start_date=start_date,
                end_date=end_date,
                next_token=token,
            )

            for item in page.data:
                yield item

            if not page.next_token:
                break

            token = page.next_token

    def get_sleep_page_sync(
        self,
        *,
        start_date: date,
        end_date: date,
        next_token: str | None = None,
    ) -> Page[SleepDocument]:
        """
        Synchronous wrapper around get_sleep_page().
        """
        return self._run(
            self.get_sleep_page(
                start_date=start_date,
                end_date=end_date,
                next_token=next_token,
            )
        )

    def iter_sleep_sync(
        self,
        *,
        start_date: date,
        end_date: date,
    ):
        """
        Synchronous wrapper around iter_sleep().
        """

        async def _collect():
            return [
                item
                async for item in self.iter_sleep(
                    start_date=start_date,
                    end_date=end_date,
                )
            ]

        return iter(self._run(_collect()))

    # ---------------------------------------------------------------------
    # Public API — Sleep Documents (Single Document)
    # ---------------------------------------------------------------------

    async def get_sleep(
        self,
        *,
        document_id: str,
    ) -> SleepDocument:
        """
        Fetch a single sleep document by ID.

        GET /v2/usercollection/sleep/{document_id}
        """
        if not document_id:
            raise ValueError("document_id must be a non-empty string")

        payload = await self._request_async(
            method="GET",
            path=f"/v2/usercollection/sleep/{document_id}",
            params=None,
        )

        return parse_sleep_document(payload)

    def get_sleep_sync(
        self,
        *,
        document_id: str,
    ) -> SleepDocument:
        """
        Synchronous wrapper around get_sleep().
        """
        return self._run(self.get_sleep(document_id=document_id))

    # ---------------------------------------------------------------------
    # Public API — Heart Rate Time-Series
    # ---------------------------------------------------------------------

    async def get_heartrate_page(
        self,
        *,
        start_datetime: date,
        end_datetime: date,
        next_token: str | None = None,
    ) -> Page[HeartRateSample]:
        """
        Fetch one page of heart-rate time-series samples.

        GET /v2/usercollection/heartrate
        """

        if start_datetime.tzinfo is None or end_datetime.tzinfo is None:
            raise ValueError("start_datetime and end_datetime must be timezone-aware")

        params: dict[str, str] = {
            "start_datetime": start_datetime.isoformat(),
            "end_datetime": end_datetime.isoformat(),
        }

        if next_token:
            params["next_token"] = next_token

        payload = await self._request_async(
            method="GET",
            path="/v2/usercollection/heartrate",
            params=params,
        )

        return parse_heartrate_page(payload)

    async def iter_heartrate(
        self,
        *,
        start_datetime: date,
        end_datetime: date,
    ):
        """
        Iterate over all HeartRateSample records in the given datetime range.
        """
        token: str | None = None

        while True:
            page = await self.get_heartrate_page(
                start_datetime=start_datetime,
                end_datetime=end_datetime,
                next_token=token,
            )

            for item in page.data:
                yield item

            if not page.next_token:
                break

            token = page.next_token

    def iter_heartrate_sync(
        self,
        *,
        start_datetime: date,
        end_datetime: date,
    ):
        """
        Synchronous wrapper around iter_heartrate().
        """

        async def _collect():
            return [
                item
                async for item in self.iter_heartrate(
                    start_datetime=start_datetime,
                    end_datetime=end_datetime,
                )
            ]

        return iter(self._run(_collect()))
