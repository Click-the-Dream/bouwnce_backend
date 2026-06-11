from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BuddyMatch:
    user_id: str
    username: str | None
    full_name: str | None
    profile_pic: dict | str | None
    bio: str | None
    distance_km: float
    score: float
    shared_interests: list[str]
    candidate_interests: list[str]


@dataclass(frozen=True)
class BuddySearchResult:
    status: str
    matches: list[BuddyMatch]
    reason: str | None = None
    has_next: bool = False
    radius_step_km: float = 10.0
