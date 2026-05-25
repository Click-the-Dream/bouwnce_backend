from __future__ import annotations

from dataclasses import dataclass

from app.matching_ground.core.location import Coordinates


@dataclass(frozen=True)
class MatchInputs:
    shared_interests: int
    total_interests: int
    user_location: Coordinates
    target_location: Coordinates
    max_distance_km: float

