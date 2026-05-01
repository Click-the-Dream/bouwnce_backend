from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UserMatchingFeatures:
    shared_interests: int
    total_interests: int


def build_user_matching_features(
    source_interests: set[str],
    target_interests: set[str],
) -> UserMatchingFeatures:
    shared_interests = len(source_interests.intersection(target_interests))
    total_interests = max(len(source_interests.union(target_interests)), 1)
    return UserMatchingFeatures(
        shared_interests=shared_interests,
        total_interests=total_interests,
    )
