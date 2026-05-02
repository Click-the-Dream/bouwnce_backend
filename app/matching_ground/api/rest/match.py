from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter,  BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

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
    return await service.suggest_candidates(
        session=db,
        requester_id=current_user.id
    )

@router.post("/requests")
async def create_match_request(
    payload: CreateMatchRequestPayload,
    db: dbSessionDep,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks
) -> dict:
    service = MatchLifecycleService()
    result = await service.create_request(
        session=db,
        requester=current_user,
        target_user_id=uuid.UUID(payload.target_user_id),
        note=payload.note,
        background_tasks=background_tasks
    )

    return {k: v for k, v in result.items() if k != "recipient_email"}


@router.get("/requests")
async def list_match_requests(
    db: dbSessionDep,
    current_user: CurrentUser,
) -> dict:
    service = MatchLifecycleService()
    return await service.list_requests_for_user(db, current_user.id)


@router.get("/")
async def list_matches(
    db: dbSessionDep,
    current_user: CurrentUser,
) -> dict:
    service = MatchLifecycleService()
    return await service.list_matches_for_user(db, current_user.id)


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
