from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.matching_ground.core.interest_normalization import normalize_interest_name
from app.models.user import User
from app.search_parser.schemas.schema import ParsedQuery


@dataclass
class BuddySearchParams:
    interest_hints: set[str]
    radius_km: float | None
    target_user_ids: set[uuid.UUID]


async def map_parsed_query_to_buddy_params(
    parsed: ParsedQuery,
    session: AsyncSession,
) -> BuddySearchParams:

    raw_interests = parsed.fields.get("interests", [])
    interest_hints: set[str] = {
        normalize_interest_name(name) for name in raw_interests if name
    }
    interest_hints.discard("")

    radius_km = parsed.fields.get("radius_km")

    raw_user_refs = parsed.fields.get("user_references", [])
    target_user_ids: set[uuid.UUID] = set()

    if raw_user_refs:
        rows = await session.execute(
            select(User.id, User.username, User.full_name).where(
                User.is_active.is_(True),
                User.is_deleted.is_(False),
            )
        )
        from app.matching_ground.service.matching.match_lifecycle import (
            MatchLifecycleService,
        )

        lifecycle = MatchLifecycleService()
        text = " ".join(raw_user_refs)

        for user_id, username, full_name in rows.all():
            candidate_score = max(
                lifecycle._score_text_match(text, username or ""),
                lifecycle._score_text_match(text, full_name or ""),
            )
            if candidate_score >= settings.SEARCH_MATCH_USER_SCORE:
                target_user_ids.add(user_id)

    return BuddySearchParams(
        interest_hints=interest_hints,
        radius_km=radius_km,
        target_user_ids=target_user_ids,
    )
