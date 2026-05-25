from __future__ import annotations

from fastapi import APIRouter, status
from pydantic import BaseModel, Field

from app.api.dependencies import CurrentAdmin, dbSessionDep, redisSessionDep
from app.matching_ground.service.admin_bouwnce_service import admin_bouwnce_service

router = APIRouter(prefix="/admin/bouwnce", tags=["Admin"])


class AdminBouwnceMessagePayload(BaseModel):
    user_ids: list[str] = Field(..., min_length=1, description="Target user ids (uuid)")
    body: str = Field(..., min_length=1, max_length=4000)


@router.post(
    "/messages",
    summary="Send a Bouwnce inbox message to users",
    status_code=status.HTTP_201_CREATED,
    response_model=dict,
)
async def send_bouwnce_message(
    payload: AdminBouwnceMessagePayload,
    db: dbSessionDep,
    redis: redisSessionDep,
    _: CurrentAdmin,
) -> dict:
    return await admin_bouwnce_service.send_message(
        db=db, redis=redis, user_ids=payload.user_ids, body=payload.body
    )
