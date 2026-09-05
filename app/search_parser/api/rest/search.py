from __future__ import annotations

from fastapi import APIRouter, Query

from app.api.dependencies import CurrentUser, dbSessionDep
from app.search_parser.schemas.responses import SearchParseResponse
from app.search_parser.service.search_service import (
    ALLOWED_DOMAINS,
    search_parser_service,
)
from app.utils.exception import BadRequestException

router = APIRouter(prefix="/search", tags=["search"])


@router.get(
    "/parse",
    summary="Parse a natural language message into structured search parameters",
    response_model=SearchParseResponse,
)
async def parse_search_message(
    db: dbSessionDep,
    current_user: CurrentUser,
    message: str = Query(..., description="Natural language search message"),
    domain: str = Query(
        ..., description=f"Search domain: {', '.join(sorted(ALLOWED_DOMAINS))}"
    ),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
) -> dict:
    if domain not in ALLOWED_DOMAINS:
        raise BadRequestException(
            message=f"Invalid domain '{domain}'. Must be one of: {', '.join(sorted(ALLOWED_DOMAINS))}",
        )

    return await search_parser_service.parse_and_search(
        session=db,
        requester_id=current_user.id,
        message=message,
        domain=domain,
        page=page,
        page_size=page_size,
    )
