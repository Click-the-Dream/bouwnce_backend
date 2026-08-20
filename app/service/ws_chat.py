"""Chat delivery mixin — send, dedup, queue, fanout, typing, dispatch.

Extracted from mobile_events_service.py to keep file sizes manageable (~500 lines).
"""

from __future__ import annotations

import asyncio
import contextlib
import time
import uuid
from typing import TYPE_CHECKING, Any

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK

from app.core.config import CHAT_EVENTS_STREAM_KEY_PREFIX, settings
from app.db.postgres_db_conn import get_async_session
from app.matching_ground.model.notification import Notification
from app.matching_ground.schema.chat import (
    ChatMessageData,
    ChatMessageEvent,
    ChatSentData,
    ChatSentEvent,
    ChatUserLite,
)
from app.matching_ground.service.chat_service import chat_service
from app.models.chat import Conversation
from app.models.user import User
from app.utils.exception import (
    BadRequestException,
    ForbiddenException,
    NotFoundException,
)
from app.worker.event_system import (
    EventNames,
    MobileEvent,
    PushNotificationEvent,
    dispatch_event,
)

if TYPE_CHECKING:
    pass

# ---------------------------------------------------------------------------
# Module-level caches for typing events (shared with main service class)
# ---------------------------------------------------------------------------
TYPING_CACHE_TTL_SECONDS = 120.0
_TYPING_CONV_CACHE: dict[str, tuple[str | None, float]] = {}
_TYPING_USER_CACHE: dict[str, tuple[ChatUserLite, float]] = {}

# Delivery dedup
CHAT_DELIVERED_KEY_PREFIX = "chat:delivered:"
CHAT_LOCAL_DELIVERY_TTL_SECONDS = 300.0
ACTIVE_CHAT_LOCAL_DELIVERIES: dict[str, float] = {}

# Connection registry (imported by main service)
ACTIVE_CHAT_CONNECTIONS: dict[
    str,
    dict[str, tuple[WebSocket, asyncio.Lock, asyncio.Queue[ChatMessageEvent]]],
] = {}


class ChatDelivery:
    """Chat send / receive / dedup / fanout logic."""

    # ------------------------------------------------------------------
    # WebSocket send helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _is_cloudinary_secure_url(url: str) -> bool:
        if not url:
            return False
        prefix = f"https://res.cloudinary.com/{settings.CLOUDINARY_NAME}/"
        return str(url).startswith(prefix)

    @staticmethod
    async def _send_json_safe(
        websocket: WebSocket,
        payload: dict,
        *,
        send_lock: asyncio.Lock | None = None,
    ) -> bool:
        try:
            if send_lock is None:
                await websocket.send_json(payload)
            else:
                async with send_lock:
                    await websocket.send_json(payload)
            return True
        except (
            WebSocketDisconnect,
            RuntimeError,
            ConnectionClosedError,
            ConnectionClosedOK,
        ):
            return False

    @staticmethod
    async def _send_text_safe(
        websocket: WebSocket,
        payload: str,
        *,
        send_lock: asyncio.Lock | None = None,
    ) -> bool:
        try:
            if send_lock is None:
                await websocket.send_text(payload)
            else:
                async with send_lock:
                    await websocket.send_text(payload)
            return True
        except (
            WebSocketDisconnect,
            RuntimeError,
            ConnectionClosedError,
            ConnectionClosedOK,
        ):
            return False

    @staticmethod
    async def _send_model_safe(
        websocket: WebSocket,
        payload,
        *,
        send_lock: asyncio.Lock | None = None,
    ) -> bool:
        from app.service.ws_chat import ChatDelivery as _CD

        return await _CD._send_json_safe(
            websocket,
            payload.model_dump(mode="json"),
            send_lock=send_lock,
        )

    # ------------------------------------------------------------------
    # Delivery dedup
    # ------------------------------------------------------------------
    async def _should_deliver_chat_message(
        self,
        *,
        redis,
        user_id: str,
        payload: ChatMessageEvent | dict,
    ) -> bool:
        if isinstance(payload, ChatMessageEvent):
            data = payload.data
            recipient_id = str(data.recipient_id)
            message_id = str(data.id).strip()
        else:
            data = payload.get("data") if isinstance(payload, dict) else None
            if not isinstance(data, dict):
                return False
            recipient_id = str(data.get("recipient_id") or "")
            message_id = str(data.get("id") or "").strip()

        if recipient_id != str(user_id):
            return False
        if not message_id:
            return False
        delivered_key = f"{CHAT_DELIVERED_KEY_PREFIX}{user_id}:{message_id}"
        if not self._claim_local_chat_delivery(delivered_key):
            return False
        with contextlib.suppress(Exception):
            return bool(
                await redis.set(
                    delivered_key,
                    "1",
                    ex=75 * 48,  # PRESENCE_TTL_SECONDS * 48
                    nx=True,
                )
            )
        return True

    @staticmethod
    def _claim_local_chat_delivery(delivered_key: str) -> bool:
        now = time.monotonic()
        if len(ACTIVE_CHAT_LOCAL_DELIVERIES) > 10000:
            expired_keys = [
                key
                for key, expires_at in ACTIVE_CHAT_LOCAL_DELIVERIES.items()
                if expires_at <= now
            ]
            for key in expired_keys:
                ACTIVE_CHAT_LOCAL_DELIVERIES.pop(key, None)

        expires_at = ACTIVE_CHAT_LOCAL_DELIVERIES.get(delivered_key)
        if expires_at is not None and expires_at > now:
            return False
        ACTIVE_CHAT_LOCAL_DELIVERIES[delivered_key] = (
            now + CHAT_LOCAL_DELIVERY_TTL_SECONDS
        )
        return True

    # ------------------------------------------------------------------
    # Direct in-process delivery
    # ------------------------------------------------------------------
    async def _send_chat_message_direct(
        self,
        *,
        redis,
        recipient_id: str,
        payload: ChatMessageEvent,
    ) -> bool:
        connections = ACTIVE_CHAT_CONNECTIONS.get(str(recipient_id))
        if not connections:
            return False
        delivered = False
        for _connection_id, (_websocket, _send_lock, chat_queue) in connections.items():
            with contextlib.suppress(Exception):
                await chat_queue.put(payload)
                delivered = True
        return delivered

    # ------------------------------------------------------------------
    # Chat queue drain
    # ------------------------------------------------------------------
    async def _drain_chat_queue(
        self,
        *,
        websocket: WebSocket,
        redis,
        user_id: str,
        chat_queue: asyncio.Queue[ChatMessageEvent],
        send_lock: asyncio.Lock,
    ) -> None:
        try:
            while True:
                payload = await chat_queue.get()
                if not await self._should_deliver_chat_message(
                    redis=redis, user_id=user_id, payload=payload
                ):
                    continue
                if not await self._send_model_safe(
                    websocket, payload, send_lock=send_lock
                ):
                    return
        except Exception:
            return

    # ------------------------------------------------------------------
    # Typing caches
    # ------------------------------------------------------------------
    @staticmethod
    def _prune_typing_caches() -> None:
        now = time.monotonic()
        for cache in (_TYPING_CONV_CACHE, _TYPING_USER_CACHE):
            if len(cache) > 10000:
                expired = [
                    key
                    for key, (_value, expires_at) in cache.items()
                    if expires_at <= now
                ]
                for key in expired:
                    cache.pop(key, None)

    async def _get_cached_conversation_id(
        self, *, db, user1_id: str, user2_id: str
    ) -> str | None:
        key = f"{min(user1_id, user2_id)}:{max(user1_id, user2_id)}"
        now = time.monotonic()
        cached = _TYPING_CONV_CACHE.get(key)
        if cached is not None and cached[1] > now:
            return cached[0]
        conv = await Conversation.get_between(
            db, uuid.UUID(str(user1_id)), uuid.UUID(str(user2_id))
        )
        conv_id = str(conv.id) if conv is not None else None
        _TYPING_CONV_CACHE[key] = (conv_id, now + TYPING_CACHE_TTL_SECONDS)
        return conv_id

    async def _get_cached_user_lite(self, *, db, user_id: str) -> ChatUserLite:
        now = time.monotonic()
        cached = _TYPING_USER_CACHE.get(user_id)
        if cached is not None and cached[1] > now:
            return cached[0]
        users = await User.get_chat_users_by_ids([str(user_id)], db)
        if not users:
            return ChatUserLite(id=uuid.UUID(str(user_id)))
        user = users[0]
        lite = ChatUserLite(
            id=user.id,
            username=user.username,
            full_name=user.full_name,
            profile_pic=chat_service._serialize_profile_pic(user),
        )
        _TYPING_USER_CACHE[user_id] = (lite, now + TYPING_CACHE_TTL_SECONDS)
        return lite

    # ------------------------------------------------------------------
    # Background side-effects (notification + push)
    # ------------------------------------------------------------------
    async def _dispatch_chat_side_effects(
        self,
        *,
        redis,
        sender: User,
        recipient_id: str,
        conversation_id: str,
        message_id: str,
        body: str,
        media_type: str | None = None,
        media_urls: list[str] | None = None,
        media_name: str | None = None,
    ) -> None:
        try:
            async with get_async_session() as db:
                notification_payload = {
                    "route": "chat.conversation",
                    "conversation_id": conversation_id,
                    "message_id": message_id,
                    "sender": chat_service._serialize_user(sender),
                }
                if media_type:
                    notification_payload["media_type"] = media_type
                    notification_payload["media_urls"] = media_urls or []
                    notification_payload["media_name"] = media_name
                await Notification.create(
                    data={
                        "user_id": recipient_id,
                        "title": sender.full_name or sender.username or "New message",
                        "body": (body or "")[:120],
                        "event_type": "chat_message",
                        "payload": notification_payload,
                    },
                    db=db,
                )
                await db.commit()

                push_payload: dict[str, Any] = {
                    "user_id": recipient_id,
                    "title": sender.full_name or sender.username or "New message",
                    "body": (body or "")[:80],
                    "data": {
                        "type": "chat.message.created",
                        "conversation_id": conversation_id,
                        "message_id": message_id,
                    },
                }
                if media_type:
                    push_payload["data"] = {
                        **push_payload["data"],
                        "media_type": media_type,
                        "media_urls": media_urls or [],
                        "media_name": media_name,
                    }

                await dispatch_event(
                    EventNames.PUSH_NOTIFICATION,
                    PushNotificationEvent(
                        user_id=recipient_id,
                        title=sender.full_name or sender.username or "New message",
                        body=(body or "")[:80],
                        data=push_payload["data"],
                    ),
                    db=db,
                    redis=redis,
                )
                await dispatch_event(
                    EventNames.MOBILE_EVENT,
                    MobileEvent(
                        event_name="chat.message.created",
                        payload={
                            "user_id": recipient_id,
                            "conversation_id": conversation_id,
                            "message_id": message_id,
                            "sender_id": str(sender.id),
                            "recipient_id": recipient_id,
                            **(
                                {
                                    "media_type": media_type,
                                    "media_urls": media_urls or [],
                                    "media_name": media_name,
                                }
                                if media_type
                                else {}
                            ),
                        },
                    ),
                    db=db,
                    redis=redis,
                )
        except Exception:
            return

    # ------------------------------------------------------------------
    # Redis fan-out
    # ------------------------------------------------------------------
    async def _publish_chat_message_fanout(
        self,
        *,
        redis,
        sender_id: str,
        recipient_id: str,
        conversation_id: str,
        payload: ChatMessageEvent,
    ) -> None:
        payload_json = payload.model_dump_json()
        await self._send_chat_message_direct(
            redis=redis, recipient_id=recipient_id, payload=payload
        )
        with contextlib.suppress(Exception):
            async with redis.pipeline() as pipe:
                pipe.publish(f"chat:conversation:{conversation_id}", payload_json)
                pipe.publish(f"chat:user:{sender_id}", payload_json)
                pipe.publish(f"chat:user:{recipient_id}", payload_json)
                pipe.xadd(
                    f"{CHAT_EVENTS_STREAM_KEY_PREFIX}{recipient_id}",
                    {"type": "chat.message", "data": payload_json},
                    maxlen=5000,
                    approximate=True,
                )
                await pipe.execute()

    # ------------------------------------------------------------------
    # Confirm + send ack
    # ------------------------------------------------------------------
    async def _confirm_chat_message_sent(
        self,
        *,
        websocket: WebSocket,
        send_lock: asyncio.Lock,
        redis,
        sender_id: str,
        recipient_id: str,
        conversation_id: str,
        payload: ChatMessageEvent,
        client_id: str | None = None,
    ) -> None:
        await self._publish_chat_message_fanout(
            redis=redis,
            sender_id=sender_id,
            recipient_id=recipient_id,
            conversation_id=conversation_id,
            payload=payload,
        )
        await self._send_model_safe(
            websocket,
            ChatSentEvent(
                client_id=client_id,
                data=ChatSentData(
                    conversation_id=payload.data.conversation_id,
                    message=payload.data,
                ),
            ),
            send_lock=send_lock,
        )

    # ------------------------------------------------------------------
    # Process incoming chat.send / chat.upload_media
    # ------------------------------------------------------------------
    async def _process_chat_send_request(
        self,
        *,
        websocket: WebSocket,
        send_lock: asyncio.Lock,
        redis,
        sender_id: str,
        recipient_id: str,
        body: str | None,
        reply_to_message_id: str | None,
        client_id: str | None,
    ) -> None:
        try:
            async with get_async_session() as db:
                sender_users = await User.get_chat_users_by_ids([str(sender_id)], db)
                if not sender_users:
                    raise NotFoundException("Sender not found")
                sender = sender_users[0]
                result = await chat_service.send_message(
                    db=db,
                    redis=redis,
                    sender=sender,
                    recipient_id=recipient_id,
                    body=body or "",
                    reply_to_message_id=reply_to_message_id,
                    commit=True,
                    as_response=False,
                    persist_notification=False,
                    notify_side_effects=False,
                    publish_redis_fanout=False,
                )
        except (
            NotFoundException,
            ForbiddenException,
            BadRequestException,
        ) as e:
            await self._send_json_safe(
                websocket,
                {
                    "type": "error",
                    "error": "chat.send.failed",
                    "message": str(e),
                },
                send_lock=send_lock,
            )
            return
        except Exception:
            return

        message_data = ChatMessageData.model_validate(result["message"])
        asyncio.create_task(
            self._dispatch_chat_side_effects(
                redis=redis,
                sender=sender,
                recipient_id=str(recipient_id),
                conversation_id=result["conversation_id"],
                message_id=str(message_data.id),
                body=body or "",
            )
        )
        await self._confirm_chat_message_sent(
            websocket=websocket,
            send_lock=send_lock,
            redis=redis,
            sender_id=str(sender_id),
            recipient_id=str(recipient_id),
            conversation_id=str(result["conversation_id"]),
            payload=ChatMessageEvent(data=message_data),
            client_id=client_id,
        )

    async def _process_chat_upload_media_request(
        self,
        *,
        websocket: WebSocket,
        send_lock: asyncio.Lock,
        redis,
        sender_id: str,
        recipient_id: str,
        body: str | None,
        media_urls: list[str],
        media_type: str,
        file_name: str | None,
        reply_to_message_id: str | None,
        client_id: str | None,
    ) -> None:
        try:
            async with get_async_session() as db:
                sender_users = await User.get_chat_users_by_ids([str(sender_id)], db)
                if not sender_users:
                    raise NotFoundException("Sender not found")
                sender = sender_users[0]
                result = await chat_service.send_media_message(
                    db=db,
                    redis=redis,
                    sender=sender,
                    recipient_id=recipient_id,
                    body=body,
                    media_urls=media_urls,
                    media_type=media_type,
                    file_name=file_name,
                    reply_to_message_id=reply_to_message_id,
                    commit=True,
                    as_response=False,
                    persist_notification=False,
                    notify_side_effects=False,
                    publish_redis_fanout=False,
                )
        except (
            NotFoundException,
            ForbiddenException,
            BadRequestException,
        ) as e:
            await self._send_json_safe(
                websocket,
                {
                    "type": "error",
                    "error": "chat.upload_media.failed",
                    "message": str(e),
                },
                send_lock=send_lock,
            )
            return
        except Exception:
            return

        message_data = ChatMessageData.model_validate(result["message"])
        asyncio.create_task(
            self._dispatch_chat_side_effects(
                redis=redis,
                sender=sender,
                recipient_id=str(recipient_id),
                conversation_id=result["conversation_id"],
                message_id=str(message_data.id),
                body=body or "",
                media_type=media_type,
                media_urls=media_urls,
                media_name=message_data.media_name,
            )
        )
        await self._confirm_chat_message_sent(
            websocket=websocket,
            send_lock=send_lock,
            redis=redis,
            sender_id=str(sender_id),
            recipient_id=str(recipient_id),
            conversation_id=str(result["conversation_id"]),
            payload=ChatMessageEvent(data=message_data),
            client_id=client_id,
        )
