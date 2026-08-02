from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.utils.responses import BaseResponse


class BuddyMatchResult(BaseModel):
    rank: int = 0
    user_id: str
    username: str
    full_name: str | None
    distance_km: float
    profile_pic: str | None
    profile_banner: str | None
    bio: str | None
    score: float
    score_explanation: str = ""
    shared_interests: list[str]
    candidate_interests: list[str]


class BuddySearchResults(BaseModel):
    matches: list[BuddyMatchResult]
    has_next: bool
    radius_step_km: float


class SearchParseData(BaseModel):
    domain: str
    raw_message: str
    parsed_fields: dict[str, Any] = Field(default_factory=dict)
    parse_source: str | None = None
    search_results: BuddySearchResults | list[Any] = Field(default_factory=list)


class SearchParseResponse(BaseResponse):
    data: SearchParseData | None = None
