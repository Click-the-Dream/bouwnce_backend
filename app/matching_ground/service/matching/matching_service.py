from __future__ import annotations

from dataclasses import dataclass

from app.matching_ground.core.location import Coordinates, haversine_km
from app.matching_ground.core.matching.aggregator import WeightedScore, aggregate
from app.matching_ground.core.matching.score import interest_overlap_score, location_score, personality_score
from app.matching_ground.core.matching.matching_feature import UserMatchingFeatures


@dataclass(frozen=True)
class MatchInputs:
    shared_interests: int
    total_interests: int
    user_location: Coordinates
    target_location: Coordinates
    max_distance_km: float


@dataclass
class MatchingService:
    weights: dict[str, float]

    def build_inputs(
        self,
        features: UserMatchingFeatures,
        user_location: Coordinates,
        target_location: Coordinates,
        max_distance_km: float,
    ) -> MatchInputs:
        return MatchInputs(
            shared_interests=features.shared_interests,
            total_interests=features.total_interests,
            user_location=user_location,
            target_location=target_location,
            max_distance_km=max_distance_km,
        )

    def score(self, inputs: MatchInputs) -> float:
        i = interest_overlap_score(inputs.shared_interests, inputs.total_interests).value
        distance = haversine_km(inputs.user_location, inputs.target_location)
        l = location_score(distance, inputs.max_distance_km).value

        scores = [
            WeightedScore(p, self.weights.get("personality", 0.0)),
            WeightedScore(i, self.weights.get("interests", 0.0)),
            WeightedScore(l, self.weights.get("location", 0.0)),
        ]
        return aggregate(scores)
