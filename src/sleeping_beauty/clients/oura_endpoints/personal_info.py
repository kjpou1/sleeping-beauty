from __future__ import annotations

from typing import Any

from sleeping_beauty.models.oura.personal_info import PersonalInfo


def parse_personal_info(payload: dict[str, Any]) -> PersonalInfo:
    """
    Parse /v2/usercollection/personal_info payload into PersonalInfo DTO.
    """
    user_id = payload.get("id")
    if not user_id:
        raise ValueError("personal_info payload missing 'id'")

    return PersonalInfo(
        user_id=user_id,
        age=payload.get("age"),
        biological_sex=payload.get("biological_sex"),
        height=payload.get("height"),
        weight=payload.get("weight"),
        email=payload.get("email"),
        raw=payload,
    )
