from __future__ import annotations

from app.matching_ground.core.location import Coordinates, haversine_km
from app.matching_ground.core.matching.aggregator import WeightedScore, aggregate
from app.matching_ground.core.matching.matching_feature import UserMatchingFeatures
from app.matching_ground.core.matching.score import (
    interest_overlap_score,
    location_score,
)
from app.matching_ground.schema.matching import MatchInputs


class MatchingService:
    def __init__(self, *, weights: dict[str, float]) -> None:
        self.weights = weights

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
        interest = interest_overlap_score(
            inputs.shared_interests, inputs.total_interests
        ).value
        distance = haversine_km(inputs.user_location, inputs.target_location)
        location = location_score(distance, inputs.max_distance_km).value

        scores = [
            WeightedScore(interest, self.weights.get("interests", 0.0)),
            WeightedScore(location, self.weights.get("location", 0.0)),
        ]
        return aggregate(scores)
