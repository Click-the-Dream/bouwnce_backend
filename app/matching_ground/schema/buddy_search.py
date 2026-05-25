from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BuddyMatch:
    user_id: str
    full_name: str | None
    profile_pic: dict | str | None
    bio: str | None
    distance_km: float
    score: float
    shared_interests: list[str]
    shared_traits: list[str]


@dataclass(frozen=True)
class BuddySearchResult:
    status: str
    matches: list[BuddyMatch]
    reason: str | None = None

