from __future__ import annotations

import uuid

from fastapi import APIRouter, Body, Query, status
from pydantic import BaseModel, Field

from app.api.dependencies import CurrentActiveUser, dbSessionDep, redisSessionDep
from app.matching_ground.service.chat_service import chat_service

router = APIRouter(prefix="/chats", tags=["Chat"])


class SendMessagePayload(BaseModel):
    recipient_id: str = Field(..., description="Recipient user id (uuid)")
    body: str = Field(..., min_length=1, max_length=4000)


@router.post(
    "/messages",
    summary="Send a message (creates conversation if needed)",
    status_code=status.HTTP_201_CREATED,
    response_model=dict,
)
async def send_message(
    payload: SendMessagePayload,
    db: dbSessionDep,
    redis: redisSessionDep,
    current_user: CurrentActiveUser,
) -> dict:
    result = await chat_service.send_message(
        db=db,
        redis=redis,
        sender=current_user,
        recipient_id=uuid.UUID(payload.recipient_id),
        body=payload.body,
    )
    await db.commit()
    return {"status": "success", "data": result}


@router.get(
    "/conversations",
    summary="List my conversations (paginated)",
    status_code=status.HTTP_200_OK,
    response_model=dict,
)
async def list_conversations(
    db: dbSessionDep,
    current_user: CurrentActiveUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> dict:
    data = await chat_service.list_conversations(
        db=db, user_id=current_user.id, page=page, page_size=page_size
    )
    return {"status": "success", "data": data}


@router.get(
    "/conversations/{conversation_id}",
    summary="Get a conversation by id",
    status_code=status.HTTP_200_OK,
    response_model=dict,
)
async def get_conversation(
    conversation_id: str,
    db: dbSessionDep,
    current_user: CurrentActiveUser,
) -> dict:
    data = await chat_service.get_conversation(
        db=db, conversation_id=uuid.UUID(conversation_id), current_user_id=current_user.id
    )
    return {"status": "success", "data": data}


@router.get(
    "/conversations/{conversation_id}/messages",
    summary="List messages in a conversation (paginated)",
    status_code=status.HTTP_200_OK,
    response_model=dict,
)
async def list_messages(
    conversation_id: str,
    db: dbSessionDep,
    current_user: CurrentActiveUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
) -> dict:
    data = await chat_service.list_messages(
        db=db,
        conversation_id=uuid.UUID(conversation_id),
        current_user_id=current_user.id,
        page=page,
        page_size=page_size,
    )
    return {"status": "success", "data": data}

