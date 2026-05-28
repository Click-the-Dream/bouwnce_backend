from __future__ import annotations

from fastapi import APIRouter, Query, status

from app.api.dependencies import CurrentActiveUser, dbSessionDep
from app.matching_ground.service.notification_service import notification_service

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get(
    "",
    summary="List notifications for current user",
    status_code=status.HTTP_200_OK,
    response_model=dict,
)
async def list_notifications(
    db: dbSessionDep,
    current_user: CurrentActiveUser,
    page: int = Query(1, gt=0),
    page_size: int = Query(20, ge=1, le=100),
) -> dict:
    return await notification_service.list_for_user(
        db=db, user_id=str(current_user.id), page=page, page_size=page_size
    )


@router.patch(
    "/{notification_id}/read",
    summary="Mark a notification as read",
    status_code=status.HTTP_200_OK,
    response_model=dict,
)
async def mark_notification_read(
    notification_id: str,
    db: dbSessionDep,
    current_user: CurrentActiveUser,
) -> dict:
    return await notification_service.mark_read(
        db=db, user_id=str(current_user.id), notification_id=notification_id
    )
