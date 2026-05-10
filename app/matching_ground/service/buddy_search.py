from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.matching_ground.core.location import Coordinates, haversine_km, within_radius
from app.matching_ground.core.interest_normalization import normalize_interest_name
from app.matching_ground.core.matching.aggregator import WeightedScore, aggregate
from app.matching_ground.core.matching.score import interest_overlap_score, location_score
from app.matching_ground.model.user_geolocation import UserGeolocation
from app.matching_ground.model.user_interest import UserInterest
from app.models.user import User
from app.matching_ground.core.matching.matching_feature import build_user_matching_features


@dataclass(frozen=True)
class BuddyMatch:
    user_id: str
    full_name: str | None
    distance_km: float
    score: float
    shared_interests: list[str]
    shared_traits: list[str]


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

    async def search(
        self,
        session: AsyncSession,
        requester_id: uuid.UUID,
        radius_km: float = 10.0,
        interest_hints: set[str] | None = None,
        limit: int = 10,
    ) -> BuddySearchResult:
        requester_geo = await self.geolocation_model.get_by_user_id(session, requester_id)
        requester_interests = {
            normalize_interest_name(i.name)
            for i in await self.interest_model.get_user_interests(session, str(requester_id))
        }

        hints = {normalize_interest_name(h) for h in (interest_hints or set()) if h}
        hints.discard("")
        if hints:
            requester_interests.update(hints)

        center = (
            Coordinates(lat=requester_geo.lat, lon=requester_geo.lon)
            if requester_geo is not None
            else None
        )

        matches: list[BuddyMatch] = []
        candidate_rows = await session.execute(
            select(
                self.user_model.id,
                self.user_model.full_name,
                self.geolocation_model.lat,
                self.geolocation_model.lon,
            )
            .outerjoin(
                self.geolocation_model, self.geolocation_model.user_id == self.user_model.id
            )
            .where(self.user_model.id != requester_id)
            .limit(max(limit * 25, 100))
        )

        for candidate_id, full_name, candidate_lat, candidate_lon in candidate_rows.all():
            if str(candidate_id) == str(requester_id):
                continue
            target = (
                Coordinates(lat=float(candidate_lat), lon=float(candidate_lon))
                if candidate_lat is not None and candidate_lon is not None
                else None
            )
            if center is not None and target is not None and not within_radius(center, target, radius_km):
                continue

            candidate_interests_rows = await self.interest_model.get_user_interests(
                session, str(candidate_id)
            )
            candidate_interests = {
                normalize_interest_name(i.name) for i in candidate_interests_rows
            }

            # If query included explicit interests, require at least one hit.
            if hints and not (candidate_interests.intersection(hints)):
                continue

            features = build_user_matching_features(
                source_interests=requester_interests,
                target_interests=candidate_interests,
            )

            interest_value = interest_overlap_score(
                features.shared_interests, features.total_interests
            ).value
            score_parts: list[WeightedScore] = [WeightedScore(interest_value, 1.0)]

            distance = -1.0
            if center is not None and target is not None:
                distance = haversine_km(center, target)
                location_value = location_score(distance, radius_km).value
                score_parts.append(WeightedScore(location_value, 1.0))

            score = aggregate(score_parts)
            matches.append(
                BuddyMatch(
                    user_id=str(candidate_id),
                    full_name=full_name,
                    distance_km=round(distance, 2) if distance >= 0 else -1.0,
                    score=round(score, 4),
                    shared_interests=sorted(
                        requester_interests.intersection(candidate_interests)
                    ),
                    shared_traits=[],
                )
            )

        matches.sort(key=lambda item: item.score, reverse=True)
        return BuddySearchResult(status="ok", matches=matches[:limit])
