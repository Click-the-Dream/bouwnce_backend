from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Score:
    value: float


def personality_score(shared_traits: int, total_traits: int) -> Score:
    if total_traits <= 0:
        return Score(0.0)
    return Score(shared_traits / total_traits)


def interest_overlap_score(shared_interests: int, total_interests: int) -> Score:
    if total_interests <= 0:
        return Score(0.0)
    return Score(shared_interests / total_interests)


def location_score(distance_km: float, max_distance_km: float) -> Score:
    if max_distance_km <= 0:
        return Score(0.0)
    value = max(0.0, 1.0 - (distance_km / max_distance_km))
    return Score(value)
