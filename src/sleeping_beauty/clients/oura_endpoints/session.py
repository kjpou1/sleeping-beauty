# sleeping_beauty/clients/oura_endpoints/session.py

from __future__ import annotations

from typing import Optional

from sleeping_beauty.models.oura.session import Session


async def get_sessions(
    client,
    *,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    next_token: Optional[str] = None,
) -> tuple[list[Session], Optional[str]]:
    params: dict[str, str] = {}

    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date
    if next_token:
        params["next_token"] = next_token

    payload = await client._request_async(
        method="GET",
        path="/v2/usercollection/session",
        params=params,
    )

    sessions = [Session.from_payload(item) for item in payload.get("data", [])]

    return sessions, payload.get("next_token")


async def get_session(
    client,
    document_id: str,
) -> Session:
    payload = await client._request_async(
        method="GET",
        path=f"/v2/usercollection/session/{document_id}",
        params=None,
    )

    return Session.from_payload(payload)
