from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Query

from app.api.dependencies import CurrentUser, dbSessionDep
from app.matching_ground.schema.match import (
    CreateMatchRequestPayload,
    RespondMatchRequestPayload,
)
from app.matching_ground.service.matching.match_lifecycle import MatchLifecycleService

router = APIRouter(prefix="/matches", tags=["matches"])


@router.get("/suggest")
async def suggest_candidates(
    db: dbSessionDep,
    current_user: CurrentUser,
) -> dict:
    service = MatchLifecycleService()
    return await service.suggest_candidates(session=db, requester_id=current_user.id)


@router.get(
    "/search",
    summary="Search match candidates from a natural language message",
)
async def search_candidates(
    db: dbSessionDep,
    current_user: CurrentUser,
    message: str | None = Query(
        None,
        description="Natural language search, e.g. 'I want someone into AI within 5km'",
    ),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
) -> dict:
    service = MatchLifecycleService()
    return await service.search_candidates_from_message(
        session=db,
        requester_id=current_user.id,
        message=message,
        page=page,
        page_size=page_size,
    )


@router.post("/requests")
async def create_match_request(
    payload: CreateMatchRequestPayload,
    db: dbSessionDep,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
) -> dict:
    service = MatchLifecycleService()
    result = await service.create_request(
        session=db,
        requester=current_user,
        target_user_id=uuid.UUID(payload.target_user_id),
        note=payload.note,
        background_tasks=background_tasks,
    )

    return {k: v for k, v in result.items() if k != "recipient_email"}


@router.get("/requests", summary="List incoming match requests for the current user")
async def list_match_requests(
    db: dbSessionDep,
    current_user: CurrentUser,
    page: Annotated[int, Query(gt=0, description="Page number")] = 1,
    page_size: Annotated[
        int, Query(gt=0, le=100, description="Number of items per page")
    ] = 10,
) -> dict:
    service = MatchLifecycleService()
    return await service.list_requests_for_user(db, current_user.id, page, page_size)


@router.get(
    "/requests/me", summary="List outgoing match requests from the current user"
)
async def list_sent_match_requests(
    db: dbSessionDep,
    current_user: CurrentUser,
    page: Annotated[int, Query(gt=0, description="Page number")] = 1,
    page_size: Annotated[
        int, Query(gt=0, le=100, description="Number of items per page")
    ] = 10,
) -> dict:
    service = MatchLifecycleService()
    return await service.list_user_sent_requests(db, current_user.id, page, page_size)


@router.get("/")
async def list_matches(
    db: dbSessionDep,
    current_user: CurrentUser,
    page: Annotated[int, Query(gt=0, description="Page number")] = 1,
    page_size: Annotated[
        int, Query(gt=0, le=100, description="Number of items per page")
    ] = 10,
) -> dict:
    service = MatchLifecycleService()
    return await service.list_matches_for_user(db, current_user.id, page, page_size)


@router.get("/{user_id}", summary="List matches for a specific user")
async def list_matches_for_user_by_id(
    user_id: uuid.UUID,
    db: dbSessionDep,
    _: CurrentUser,
    page: Annotated[int, Query(gt=0, description="Page number")] = 1,
    page_size: Annotated[
        int, Query(gt=0, le=100, description="Number of items per page")
    ] = 10,
):
    return await MatchLifecycleService().list_matches_for_user(
        db, user_id, page=page, page_size=page_size
    )


@router.post("/requests/{request_id}/respond")
async def respond_match_request(
    request_id: str,
    payload: RespondMatchRequestPayload,
    db: dbSessionDep,
    current_user: CurrentUser,
) -> dict:
    service = MatchLifecycleService()
    return await service.respond_request(
        session=db,
        request_id=uuid.UUID(request_id),
        responder_user_id=current_user.id,
        accepted=payload.accepted,
    )
