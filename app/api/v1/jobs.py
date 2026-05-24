from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, status
from pydantic import BaseModel, Field

from app.api.dependencies import dbSessionDep
from app.service.newsletter import newsletter_service


class NewletterBroadcastRequest(BaseModel):
    newsletter_id: Annotated[str, Field(description="Newsletter ID")]


router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.post(
    "/execute/broadcast-newsletter",
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def broadcast_newsletter(
    newsletter_payload: NewletterBroadcastRequest,
    db: dbSessionDep,
    background_task: BackgroundTasks,
):
    return await newsletter_service.broadcast_newsletter(
        newsletter_payload.newsletter_id, db, background_task
    )
