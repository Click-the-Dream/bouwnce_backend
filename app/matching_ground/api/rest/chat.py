from __future__ import annotations

import uuid

import asyncio
import json

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.dependencies import CurrentActiveUser, dbSessionDep, redisSessionDep
from app.core.security import verify_token
from app.db.postgres_db_conn import get_async_session
from app.db.redis import get_redis_client
from app.matching_ground.schema.chat import SendMessagePayload
from app.matching_ground.service.chat_service import chat_service
from app.models.chat import Conversation
from app.models.user import User

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


@router.websocket("/ws/conversations/{conversation_id}")
async def chat_ws(websocket: WebSocket, conversation_id: str) -> None:
    """
    WebSocket chat channel backed by Redis PubSub.
    Auth: pass access token via query string `?token=...`.

    Client -> server:
      { "type": "message", "body": "hi" }
    Server -> client:
      { "type": "chat.message", "data": {...message dict...} }
    """
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008)
        return

    payload = verify_token(token)
    if payload.get("type") != "access":
        await websocket.close(code=1008)
        return

    user_id = payload.get("sub")
    if not user_id:
        await websocket.close(code=1008)
        return

    conv_uuid = uuid.UUID(conversation_id)
    pubsub_channel = f"chat:conversation:{conversation_id}"

    redis = await get_redis_client()
    pubsub = redis.pubsub()
    await pubsub.subscribe(pubsub_channel)

    async with get_async_session() as db:
        # Validate membership + get recipient id
        result = await db.execute(
            select(Conversation)
            .where(Conversation.id == conv_uuid)
            .options(selectinload(Conversation.user_a), selectinload(Conversation.user_b))
        )
        conv = result.scalar_one_or_none()
        if not conv:
            await websocket.close(code=1008)
            await pubsub.unsubscribe(pubsub_channel)
            await pubsub.close()
            return

        current_id = uuid.UUID(str(user_id))
        if current_id not in {conv.user_a_id, conv.user_b_id}:
            await websocket.close(code=1008)
            await pubsub.unsubscribe(pubsub_channel)
            await pubsub.close()
            return

        recipient_id = conv.user_b_id if current_id == conv.user_a_id else conv.user_a_id

        await websocket.accept()

        async def forward_pubsub() -> None:
            try:
                async for msg in pubsub.listen():
                    if msg is None:
                        continue
                    if msg.get("type") != "message":
                        continue
                    data = msg.get("data")
                    # decode_responses=True => str, else bytes
                    if isinstance(data, (bytes, bytearray)):
                        data = data.decode()
                    await websocket.send_text(data)
            except Exception:
                return

        forward_task = asyncio.create_task(forward_pubsub())

        try:
            while True:
                raw = await websocket.receive_text()
                try:
                    incoming = json.loads(raw)
                except Exception:
                    continue

                if incoming.get("type") != "message":
                    continue

                body = str(incoming.get("body") or "").strip()
                if not body:
                    continue

                sender = await User.get_by_id(str(current_id), db)
                result = await chat_service.send_message(
                    db=db,
                    redis=redis,
                    sender=sender,
                    recipient_id=recipient_id,
                    body=body,
                )
                await db.commit()
                # send immediately back to sender too
                await websocket.send_json({"type": "chat.message.sent", "data": result})

        except WebSocketDisconnect:
            pass
        finally:
            forward_task.cancel()
            await pubsub.unsubscribe(pubsub_channel)
            await pubsub.close()
