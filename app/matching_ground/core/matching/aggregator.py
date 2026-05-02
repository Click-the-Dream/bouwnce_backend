from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WeightedScore:
    score: float
    weight: float


def aggregate(scores: list[WeightedScore]) -> float:
    if not scores:
        return 0.0
    total_weight = sum(s.weight for s in scores)
    if total_weight <= 0:
        return 0.0
    weighted_sum = sum(s.score * s.weight for s in scores)
    return weighted_sum / total_weight
