from __future__ import annotations

import uuid

from fastapi import APIRouter, Query, status

from app.api.dependencies import CurrentActiveUser, dbSessionDep, redisSessionDep
from app.matching_ground.schema.chat import SendMessagePayload
from app.matching_ground.service.chat_service import chat_service

router = APIRouter(prefix="/chats", tags=["Chat"])


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
    return await chat_service.send_message(
        db=db,
        redis=redis,
        sender=current_user,
        recipient_id=payload.recipient_id,
        body=payload.body,
        commit=True,
        as_response=True,
    )


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
    return await chat_service.list_conversations(
        db=db, user_id=current_user.id, page=page, page_size=page_size, as_response=True
    )


@router.get(
    "/conversations/{conversation_id}",
    summary="Get a conversation by id",
    status_code=status.HTTP_200_OK,
    response_model=dict,
)
async def get_conversation(
    conversation_id: uuid.UUID,
    db: dbSessionDep,
    current_user: CurrentActiveUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
) -> dict:
    return await chat_service.get_conversation(
        db=db,
        current_user_id=current_user.id,
        conversation_id=conversation_id,
        include_messages=True,
        messages_page=page,
        messages_page_size=page_size,
        as_response=True,
    )

@router.get(
    "/conversations/with/{user_id}",
    summary="Get or create a conversation with a user",
    status_code=status.HTTP_200_OK,
    response_model=dict,
)
async def get_conversation_with_user(
    user_id: uuid.UUID,
    db: dbSessionDep,
    current_user: CurrentActiveUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
) -> dict:
    return await chat_service.get_or_create_conversation_with_user(
        db=db,
        current_user_id=current_user.id,
        user_id=user_id,
        include_messages=True,
        messages_page=page,
        messages_page_size=page_size,
        commit=True,
        as_response=True,
    )

@router.get(
    "/conversations/{conversation_id}/messages",
    summary="List messages in a conversation (paginated)",
    status_code=status.HTTP_200_OK,
    response_model=dict,
)
async def list_messages(
    conversation_id: uuid.UUID,
    db: dbSessionDep,
    current_user: CurrentActiveUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
) -> dict:
    return await chat_service.list_messages(
        db=db,
        current_user_id=current_user.id,
        conversation_id=conversation_id,
        page=page,
        page_size=page_size,
        as_response=True,
    )
