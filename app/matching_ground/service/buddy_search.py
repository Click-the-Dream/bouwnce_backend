from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.matching_ground.core.location import Coordinates, haversine_km, within_radius
from app.matching_ground.core.interest_normalization import normalize_interest_name
from app.matching_ground.model.user_geolocation import UserGeolocation
from app.matching_ground.model.user_interest import UserInterest
from app.models.user import User
from app.matching_ground.core.matching.matching_feature import build_user_matching_features
from app.matching_ground.service.matching.matching_service import MatchingService


@dataclass(frozen=True)
class BuddyMatch:
    user_id: str
    full_name: str | None
    distance_km: float
    score: float
    shared_interests: list[str]


@dataclass(frozen=True)
class BuddySearchResult:
    status: str
    matches: list[BuddyMatch]
    reason: str | None = None


class BuddySearchService:
    def __init__(
        self,
    ) -> None:
        self.geolocation_model = UserGeolocation
        self.interest_model = UserInterest
        self.user_model = User
        self.matching = MatchingService(weights={"personality": 0.35, "interests": 0.4, "location": 0.25})

    async def search(
        self,
        session: AsyncSession,
        requester_id: uuid.UUID,
        radius_km: float = 10.0,
        interest_hint: str | None = None,
        limit: int = 10,
    ) -> BuddySearchResult:
        requester_geo = await self.geolocation_model.get_by_user_id(session, requester_id)
        if requester_geo is None:
            return BuddySearchResult(status="location_required", matches=[], reason="requester_location_missing")

        requester_interests = {i.name for i in await self.interest_model.get_user_interests(session, str(requester_id))}

        hint = normalize_interest_name(interest_hint) if interest_hint else None
        center = Coordinates(lat=requester_geo.lat, lon=requester_geo.lon)

        matches: list[BuddyMatch] = []
        candidates = await self.geolocation_model.list_others(session, requester_id)
        for candidate_geo in candidates:
            target = Coordinates(lat=candidate_geo.lat, lon=candidate_geo.lon)
            if not within_radius(center, target, radius_km):
                continue

            candidate_interests_rows = await self.interest_model.get_user_interests(session, str(candidate_geo.user_id))
            candidate_interests = {i.name for i in candidate_interests_rows}


            features = build_user_matching_features(
                source_interests=requester_interests,
                target_interests=candidate_interests,
            )
            inputs = self.matching.build_inputs(
                features=features,
                user_location=center,
                target_location=target,
                max_distance_km=radius_km,
            )
            score = self.matching.score(inputs)
            distance = haversine_km(center, target)
            profile = await self.user_model.get_by_id( str(candidate_geo.user_id), session)
            full_name = profile.full_name if profile else None
            matches.append(
                BuddyMatch(
                    user_id=str(candidate_geo.user_id),
                    full_name=full_name,
                    distance_km=round(distance, 2),
                    score=round(score, 4),
                    shared_interests=sorted(requester_interests.intersection(candidate_interests))
                )
            )

        matches.sort(key=lambda item: item.score, reverse=True)
        return BuddySearchResult(status="ok", matches=matches[:limit])
