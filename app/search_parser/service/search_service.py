from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.search_parser.schemas.schema import BuddySearchQuery, get_domain_config
from app.search_parser.search_parser import CompositeQueryParser
from app.utils.exception import InternalServerErrorException
from app.utils.responses import response_builder

ALLOWED_DOMAINS = {"buddy", "product"}

_W_HINT_MATCH = 0.50
_W_SHARED_COUNT = 0.30
_W_PROXIMITY = 0.20


def _rescore_match(
    *,
    base_score: float,
    hint_matched: bool,
    shared_interests_count: int,
    max_shared: int,
    distance_km: float,
    radius_km: float,
) -> float:

    hint_val = 1.0 if hint_matched else 0.0

    shared_val = (
        min(shared_interests_count / max_shared, 1.0) if max_shared > 0 else 0.0
    )

    if distance_km >= 0 and radius_km > 0:
        prox_val = max(0.0, 1.0 - distance_km / radius_km)
    else:
        prox_val = 0.0

    return round(
        hint_val * _W_HINT_MATCH
        + shared_val * _W_SHARED_COUNT
        + prox_val * _W_PROXIMITY,
        4,
    )


def _build_score_explanation(
    *,
    score: float,
    hint_matched: bool,
    distance_km: float,
    matched_interests: list[str],
    shared_interests_count: int,
) -> str:
    basis_parts: list[str] = []
    if matched_interests:
        basis_parts.append(f"interests:{','.join(matched_interests)}")
    if not hint_matched and not matched_interests:
        basis_parts.append("proximity")
    basis = ",".join(basis_parts) if basis_parts else "proximity"

    match_tag = "YES" if hint_matched else "NO"
    return (
        f"score={score}, "
        f"hint_match={match_tag}, "
        f"distance={distance_km}km, "
        f"shared_interests={shared_interests_count}, "
        f"based_on={basis}"
    )


class SearchParserService:
    def __init__(self) -> None:
        self._parser = CompositeQueryParser()

    async def parse_and_search(
        self,
        session: AsyncSession,
        requester_id: uuid.UUID,
        message: str,
        domain: str,
        page: int,
        page_size: int,
    ) -> dict:
        try:
            parsed = await self._parser.parse_with_session(
                session=session,
                message=message,
                domain_name=domain,
                requester_id=requester_id,
            )
        except Exception as exc:
            raise InternalServerErrorException(
                message=f"Search parsing failed: {exc}"
            ) from exc

        if parsed is None:
            return response_builder(
                status_code=200,
                message="No parse result",
                data={
                    "domain": domain,
                    "raw_message": message,
                    "parsed_fields": {},
                    "search_results": [],
                },
            )

        domain_config = get_domain_config(domain)

        if domain_config.output_model == BuddySearchQuery:
            return await self._search_buddies(
                session=session,
                requester_id=requester_id,
                parsed=parsed,
                domain=domain,
                message=message,
                page=page,
                page_size=page_size,
            )

        return response_builder(
            status_code=200,
            message="Search parsed successfully",
            data={
                "domain": domain,
                "raw_message": message,
                "parsed_fields": parsed.fields,
                "parse_source": parsed.source,
                "search_results": [],
            },
        )

    async def _search_buddies(
        self,
        session: AsyncSession,
        requester_id: uuid.UUID,
        parsed: object,
        domain: str,
        message: str,
        page: int,
        page_size: int,
    ) -> dict:
        from app.matching_ground.service.buddy_search import BuddySearchService
        from app.search_parser.service.buddy_param_mapper import (
            map_parsed_query_to_buddy_params,
        )

        try:
            params = await map_parsed_query_to_buddy_params(parsed, session)
        except Exception as exc:
            raise InternalServerErrorException(
                message=f"Failed to map parsed query to buddy params: {exc}"
            ) from exc

        buddy_service = BuddySearchService()
        try:
            result = await buddy_service.search(
                session=session,
                requester_id=requester_id,
                radius_km=params.radius_km or 10.0,
                interest_hints=params.interest_hints,
                target_user_ids=params.target_user_ids,
                page=page,
                page_size=page_size,
            )
        except Exception as exc:
            raise InternalServerErrorException(
                message=f"Buddy search failed: {exc}"
            ) from exc

        radius_km = params.radius_km or 10.0
        hint_norms = {h.lower() for h in params.interest_hints}

        # Pre-compute max shared interests for normalization
        max_shared = max((len(m.shared_interests) for m in result.matches), default=0)

        # Rescore, filter, and rank
        scored: list[tuple[float, object]] = []
        for m in result.matches:
            matched_interests = [
                si for si in m.shared_interests if si.lower() in hint_norms
            ]
            hint_matched = len(matched_interests) > 0

            new_score = _rescore_match(
                base_score=m.score,
                hint_matched=hint_matched,
                shared_interests_count=len(m.shared_interests),
                max_shared=max_shared,
                distance_km=m.distance_km,
                radius_km=radius_km,
            )

            if not hint_matched and not m.shared_interests:
                continue

            scored.append((new_score, m, matched_interests))

        scored.sort(key=lambda x: x[0], reverse=True)

        matches_data = []
        for rank, (new_score, m, matched_interests) in enumerate(scored, start=1):
            matches_data.append(
                {
                    "rank": rank,
                    "user_id": m.user_id,
                    "username": m.username,
                    "full_name": m.full_name,
                    "distance_km": m.distance_km,
                    "profile_pic": m.profile_pic,
                    "profile_banner": m.profile_banner,
                    "bio": m.bio,
                    "score": new_score,
                    "score_explanation": _build_score_explanation(
                        score=new_score,
                        hint_matched=bool(matched_interests),
                        distance_km=m.distance_km,
                        matched_interests=matched_interests,
                        shared_interests_count=len(m.shared_interests),
                    ),
                    "shared_interests": m.shared_interests,
                    "candidate_interests": m.candidate_interests,
                }
            )

        return response_builder(
            status_code=200,
            message="Search parsed successfully",
            data={
                "domain": domain,
                "raw_message": message,
                "parsed_fields": parsed.fields,
                "parse_source": parsed.source,
                "search_results": {
                    "matches": matches_data,
                    "has_next": result.has_next,
                    "radius_step_km": result.radius_step_km,
                },
            },
        )


search_parser_service = SearchParserService()
