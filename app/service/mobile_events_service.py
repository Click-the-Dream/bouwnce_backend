"""WebSocket event handler — entry-point class composing Chat + Presence mixins.

The heavy logic lives in:
  - ws_chat.py      (ChatDelivery)    — send / dedup / queue / fanout / typing
  - ws_presence.py  (PresenceManager) — bootstrap / presence / forwarders

This file (~400 lines) stays small: it wires everything together via handle_ws.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import uuid

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK

from app.core.security import verify_token
from app.db.postgres_db_conn import get_async_session
from app.db.redis import get_redis_client
from app.matching_ground.schema.chat import (
    ChatMessageEvent,
    ChatReadAckData,
    ChatReadAckEvent,
    ChatReadyData,
    ChatReadyEvent,
    ChatSendAckData,
    ChatSendAckEvent,
    ChatTypingData,
    ChatTypingEvent,
    MarkConversationReadPayload,
    PongEvent,
    SendMessagePayload,
    TypingPayload,
    UploadMediaPayload,
)
from app.matching_ground.service.chat_service import chat_service
from app.models.chat import Conversation
from app.models.user import User
from app.service.ws_chat import ACTIVE_CHAT_CONNECTIONS, ChatDelivery  # noqa: F401
from app.service.ws_presence import (
    PRESENCE_KEY_PREFIX,
    PresenceManager,
)
from app.utils.exception import (
    BadRequestException,
    ForbiddenException,
    InternalServerErrorException,
    NotFoundException,
)


class MobileEventsService(ChatDelivery, PresenceManager):
    """Composed WebSocket handler — inherits chat + presence logic."""

    async def handle_ws(self, websocket: WebSocket) -> None:
        token = websocket.query_params.get("token")
        if not token:
            await websocket.close(code=1008)
            return

        token_payload = verify_token(token)
        if token_payload.get("type") != "access":
            await websocket.close(code=1008)
            return

        user_id = token_payload.get("sub")
        if not user_id:
            await websocket.close(code=1008)
            return

        pubsub = None
        try:
            redis = await get_redis_client()
            pubsub = redis.pubsub()
            await pubsub.subscribe(f"chat:user:{user_id}")
        except Exception:
            if pubsub is not None:
                with contextlib.suppress(Exception):
                    await pubsub.aclose()
            with contextlib.suppress(Exception):
                await websocket.close(code=1013)
            return

        await websocket.accept()
        send_lock = asyncio.Lock()
        chat_queue: asyncio.Queue[ChatMessageEvent] = asyncio.Queue(maxsize=200)
        connection_id = uuid.uuid4().hex
        ACTIVE_CHAT_CONNECTIONS.setdefault(str(user_id), {})[connection_id] = (
            websocket,
            send_lock,
            chat_queue,
        )
        chat_stream_ready = asyncio.Event()
        pubsub_task = asyncio.create_task(
            self._forward_pubsub(
                websocket=websocket,
                pubsub=pubsub,
                redis=redis,
                user_id=str(user_id),
                send_lock=send_lock,
            )
        )
        chat_stream_task = asyncio.create_task(
            self._forward_chat_stream(
                websocket=websocket,
                redis=redis,
                user_id=str(user_id),
                ready_event=chat_stream_ready,
                send_lock=send_lock,
            )
        )
        bootstrap_task = asyncio.create_task(
            self._bootstrap_connection(
                websocket=websocket,
                redis=redis,
                user_id=str(user_id),
                send_lock=send_lock,
            )
        )
        chat_queue_task = asyncio.create_task(
            self._drain_chat_queue(
                websocket=websocket,
                redis=redis,
                user_id=str(user_id),
                chat_queue=chat_queue,
                send_lock=send_lock,
            )
        )
        presence_task = asyncio.create_task(
            self._presence_heartbeat(redis=redis, user_id=str(user_id))
        )

        # Wait for bootstrap + stream ready before sending chat.ready
        with contextlib.suppress(Exception):
            await bootstrap_task
        with contextlib.suppress(Exception):
            await asyncio.wait_for(chat_stream_ready.wait(), timeout=5)

        await self._send_model_safe(
            websocket,
            ChatReadyEvent(data=ChatReadyData(user_id=str(user_id))),
            send_lock=send_lock,
        )

        try:
            while True:
                try:
                    raw = await websocket.receive_text()
                except (
                    WebSocketDisconnect,
                    RuntimeError,
                    ConnectionClosedError,
                    ConnectionClosedOK,
                ):
                    break
                incoming = None
                with contextlib.suppress(Exception):
                    incoming = json.loads(raw)
                if incoming is None:
                    continue

                msg_type = str(incoming.get("type") or "").strip().lower()
                if not msg_type:
                    continue

                # ---- ping ----
                if msg_type == "ping":
                    if not await self._send_model_safe(
                        websocket, PongEvent(), send_lock=send_lock
                    ):
                        break
                    continue

                # ---- chat.send ----
                if msg_type == "chat.send":
                    if not await self._handle_chat_send(
                        websocket, send_lock, redis, user_id, incoming
                    ):
                        break
                    continue

                # ---- chat.upload_media ----
                if msg_type == "chat.upload_media":
                    if not await self._handle_chat_upload_media(
                        websocket, send_lock, redis, user_id, incoming
                    ):
                        break
                    continue

                # ---- chat.read ----
                if msg_type == "chat.read":
                    if not await self._handle_chat_read(
                        websocket, send_lock, redis, user_id, incoming
                    ):
                        break
                    continue

                # ---- chat.typing ----
                if msg_type == "chat.typing":
                    if not await self._handle_chat_typing(
                        websocket, send_lock, redis, user_id, incoming
                    ):
                        break
                    continue
        finally:
            user_connections = ACTIVE_CHAT_CONNECTIONS.get(str(user_id))
            if user_connections is not None:
                user_connections.pop(connection_id, None)
                if not user_connections:
                    ACTIVE_CHAT_CONNECTIONS.pop(str(user_id), None)
            bootstrap_task.cancel()
            pubsub_task.cancel()
            chat_stream_task.cancel()
            chat_queue_task.cancel()
            presence_task.cancel()
            with contextlib.suppress(Exception):
                await pubsub.unsubscribe(f"chat:user:{user_id}")
            with contextlib.suppress(Exception):
                await pubsub.aclose()
            await asyncio.gather(
                bootstrap_task,
                pubsub_task,
                chat_stream_task,
                chat_queue_task,
                presence_task,
                return_exceptions=True,
            )
            with contextlib.suppress(Exception):
                await redis.delete(f"{PRESENCE_KEY_PREFIX}{user_id}")
                await self._publish_presence(
                    redis=redis, user_id=str(user_id), online=False
                )

    # ------------------------------------------------------------------
    # Event handlers (extracted from the main loop for readability)
    # ------------------------------------------------------------------
    async def _handle_chat_send(
        self, websocket: WebSocket, send_lock, redis, user_id: str, incoming: dict
    ) -> bool:
        """Handle chat.send. Returns False if the connection should close."""
        try:
            payload = SendMessagePayload.model_validate(incoming)
        except Exception:
            return await self._send_json_safe(
                websocket,
                {
                    "type": "error",
                    "error": "invalid_payload",
                    "message": "Expected: {type:'chat.send', recipient_id:'<uuid>', body:'...'}",
                },
                send_lock=send_lock,
            )

        if not await self._send_model_safe(
            websocket,
            ChatSendAckEvent(
                data=ChatSendAckData(
                    sender_id=uuid.UUID(str(user_id)),
                    recipient_id=payload.recipient_id,
                    client_id=payload.client_id,
                )
            ),
            send_lock=send_lock,
        ):
            return False

        asyncio.create_task(
            self._process_chat_send_request(
                websocket=websocket,
                send_lock=send_lock,
                redis=redis,
                sender_id=str(user_id),
                recipient_id=str(payload.recipient_id),
                body=payload.body,
                reply_to_message_id=(
                    str(payload.reply_to_message_id)
                    if payload.reply_to_message_id
                    else None
                ),
                client_id=payload.client_id,
            )
        )
        return True

    async def _handle_chat_upload_media(
        self, websocket: WebSocket, send_lock, redis, user_id: str, incoming: dict
    ) -> bool:
        """Handle chat.upload_media. Returns False if the connection should close."""
        try:
            payload = UploadMediaPayload.model_validate(incoming)
        except Exception:
            return await self._send_json_safe(
                websocket,
                {
                    "type": "error",
                    "error": "invalid_payload",
                    "message": "Expected: {type:'chat.upload_media', recipient_id:'<uuid>', media_type:'image|video|file', media_urls:['https://...'], body?:'...'}",
                },
                send_lock=send_lock,
            )

        if str(payload.recipient_id) == str(user_id):
            return await self._send_json_safe(
                websocket,
                {"type": "error", "error": "self_send_not_allowed"},
                send_lock=send_lock,
            )

        media_type = (payload.media_type or "").strip().lower()
        if media_type not in {"image", "video", "file"}:
            return await self._send_json_safe(
                websocket,
                {"type": "error", "error": "invalid_media_type"},
                send_lock=send_lock,
            )

        urls = [u for u in (payload.media_urls or []) if u]
        if not urls:
            return await self._send_json_safe(
                websocket,
                {"type": "error", "error": "missing_media_urls"},
                send_lock=send_lock,
            )

        if not await self._send_model_safe(
            websocket,
            ChatSendAckEvent(
                data=ChatSendAckData(
                    sender_id=uuid.UUID(str(user_id)),
                    recipient_id=payload.recipient_id,
                    client_id=payload.client_id,
                )
            ),
            send_lock=send_lock,
        ):
            return False

        if any(not self._is_cloudinary_secure_url(u) for u in urls):
            return await self._send_json_safe(
                websocket,
                {"type": "error", "error": "invalid_media_urls"},
                send_lock=send_lock,
            )

        asyncio.create_task(
            self._process_chat_upload_media_request(
                websocket=websocket,
                send_lock=send_lock,
                redis=redis,
                sender_id=str(user_id),
                recipient_id=str(payload.recipient_id),
                body=payload.body,
                media_urls=urls,
                media_type=media_type,
                file_name=payload.file_name,
                reply_to_message_id=(
                    str(payload.reply_to_message_id)
                    if payload.reply_to_message_id
                    else None
                ),
                client_id=payload.client_id,
            )
        )
        return True

    async def _handle_chat_read(
        self, websocket: WebSocket, send_lock, redis, user_id: str, incoming: dict
    ) -> bool:
        """Handle chat.read. Returns False if the connection should close."""
        try:
            payload = MarkConversationReadPayload.model_validate(incoming)
        except Exception:
            return await self._send_json_safe(
                websocket,
                {
                    "type": "error",
                    "error": "invalid_payload",
                    "message": "Expected: {type:'chat.read', recipient_id:'<uuid>', mark_all?:true|false, message_id?:'<uuid>'}",
                },
                send_lock=send_lock,
            )

        async with get_async_session() as db:
            try:
                if payload.mark_all:
                    conv = await Conversation.get_between(
                        db,
                        uuid.UUID(str(user_id)),
                        uuid.UUID(str(payload.recipient_id)),
                    )
                    if conv is None:
                        raise NotFoundException("Conversation not found")
                    result = await chat_service.mark_conversation_read(
                        db=db,
                        redis=redis,
                        current_user_id=str(user_id),
                        conversation_id=str(conv.id),
                        commit=False,
                        as_response=False,
                    )
                else:
                    if payload.message_id is None:
                        raise BadRequestException(
                            "message_id is required when mark_all is false"
                        )
                    result = await chat_service.mark_conversation_read_with_user_up_to_message(
                        db=db,
                        redis=redis,
                        current_user_id=str(user_id),
                        recipient_id=str(payload.recipient_id),
                        message_id=str(payload.message_id),
                        commit=False,
                        as_response=False,
                    )
            except (
                NotFoundException,
                ForbiddenException,
                BadRequestException,
            ) as e:
                return await self._send_json_safe(
                    websocket,
                    {"type": "error", "error": "chat.read.failed", "message": str(e)},
                    send_lock=send_lock,
                )

        return await self._send_model_safe(
            websocket,
            ChatReadAckEvent(data=ChatReadAckData.model_validate(result)),
            send_lock=send_lock,
        )

    async def _handle_chat_typing(
        self, websocket: WebSocket, send_lock, redis, user_id: str, incoming: dict
    ) -> bool:
        """Handle chat.typing. Returns False if the connection should close."""
        self._prune_typing_caches()
        try:
            payload = TypingPayload.model_validate(incoming)
        except Exception:
            return await self._send_json_safe(
                websocket,
                {
                    "type": "error",
                    "error": "invalid_payload",
                    "message": "Expected: {type:'chat.typing', user_id:'<uuid>', is_typing:true|false}",
                },
                send_lock=send_lock,
            )

        async with get_async_session() as db:
            try:
                conv_id = await self._get_cached_conversation_id(
                    db=db,
                    user1_id=str(user_id),
                    user2_id=str(payload.user_id),
                )
                if conv_id is None:
                    raise NotFoundException("Conversation not found")

                sender_lite = await self._get_cached_user_lite(
                    db=db, user_id=str(user_id)
                )
                # Pre-warm Redis cache for recipient
                await User.get_chat_users_by_ids([str(payload.user_id)], db)
                targets = {str(user_id), str(payload.user_id)}
            except (
                NotFoundException,
                ForbiddenException,
                BadRequestException,
            ) as e:
                return await self._send_json_safe(
                    websocket,
                    {"type": "error", "error": "chat.typing.failed", "message": str(e)},
                    send_lock=send_lock,
                )

        event_payload = ChatTypingEvent(
            data=ChatTypingData(
                conversation_id=uuid.UUID(str(conv_id)),
                user=sender_lite,
                is_typing=bool(payload.is_typing),
            )
        )
        try:
            async with redis.pipeline() as pipe:
                for target_id in targets:
                    pipe.publish(
                        f"chat:user:{target_id}",
                        event_payload.model_dump_json(),
                    )
                await pipe.execute()
        except Exception as e:
            raise InternalServerErrorException("Failed to publish typing event") from e

        return True


mobile_events_service = MobileEventsService()
