from __future__ import annotations

import asyncio
import contextlib
import json
import uuid
from typing import Any

from fastapi import WebSocket
from pydantic import BaseModel
from sqlalchemy import func, select
from starlette.websockets import WebSocketDisconnect
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK

from app.core.config import (
    CHAT_EVENTS_LAST_ID_KEY_PREFIX,
    CHAT_EVENTS_STREAM_KEY_PREFIX,
    MOBILE_EVENTS_STREAM_KEY,
    PAYMENT_PROGRESS_KEY_PREFIX,
    settings,
)
from app.core.security import verify_token
from app.db.postgres_db_conn import get_async_session
from app.db.redis import get_redis_client
from app.matching_ground.model.notification import Notification
from app.matching_ground.schema.chat import (
    ChatMessageData,
    ChatMessageEvent,
    ChatReadAckData,
    ChatReadAckEvent,
    ChatReadyData,
    ChatReadyEvent,
    ChatSentData,
    ChatSentEvent,
    ChatTypingData,
    ChatTypingEvent,
    ChatUserLite,
    MarkConversationReadPayload,
    PongEvent,
    SendMessagePayload,
    TypingPayload,
    UploadMediaPayload,
)
from app.matching_ground.service.bouwnce_dm_service import bouwnce_dm_service
from app.matching_ground.service.chat_service import chat_service
from app.models.chat import Conversation, Message
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

PRESENCE_KEY_PREFIX = "presence:user:"
PRESENCE_TTL_SECONDS = 75
ACTIVE_CHAT_CONNECTIONS: dict[
    str,
    dict[str, tuple[WebSocket, asyncio.Lock, asyncio.Queue[ChatMessageEvent]]],
] = {}


class MobileEventsService:
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
        payload: BaseModel,
        *,
        send_lock: asyncio.Lock | None = None,
    ) -> bool:
        return await MobileEventsService._send_json_safe(
            websocket,
            payload.model_dump(mode="json"),
            send_lock=send_lock,
        )

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
            data = payload.get("data")
            if not isinstance(data, dict):
                return False
            recipient_id = str(data.get("recipient_id") or "")
            message_id = str(data.get("id") or "").strip()

        if recipient_id != str(user_id):
            return False
        if not message_id:
            return False
        delivered_key = f"chat:delivered:{user_id}:{message_id}"
        return bool(
            await redis.set(
                delivered_key,
                "1",
                ex=PRESENCE_TTL_SECONDS * 48,
                nx=True,
            )
        )

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

    async def _bootstrap_connection(
        self,
        *,
        websocket: WebSocket,
        redis,
        user_id: str,
        send_lock: asyncio.Lock,
    ) -> None:
        with contextlib.suppress(Exception):
            async with get_async_session() as db:
                system_user = await bouwnce_dm_service.get_system_user(db=db)
                if system_user is not None:
                    await self._send_json_safe(
                        websocket,
                        {
                            "type": "bouwnce.system",
                            "data": {
                                "user": {
                                    "id": str(system_user.id),
                                    "email": system_user.email,
                                    "username": system_user.username,
                                    "full_name": system_user.full_name,
                                    "profile_pic": chat_service._serialize_profile_pic(
                                        system_user
                                    ),
                                }
                            },
                        },
                        send_lock=send_lock,
                    )

        with contextlib.suppress(Exception):
            async with get_async_session() as db:
                await bouwnce_dm_service.ensure_welcome_conversation(
                    db=db, redis=redis, user_id=str(user_id), commit=True
                )

        await redis.set(f"{PRESENCE_KEY_PREFIX}{user_id}", "1", ex=PRESENCE_TTL_SECONDS)
        await self._publish_presence(redis=redis, user_id=str(user_id), online=True)

        with contextlib.suppress(Exception):
            await self._send_presence_snapshot(
                websocket=websocket,
                redis=redis,
                user_id=str(user_id),
                send_lock=send_lock,
            )

    async def read_mobile_events(
        self,
        *,
        redis,
        user_id: str,
        last_id: str,
        block_ms: int,
        count: int,
    ) -> dict:
        streams = await redis.xread(
            streams={MOBILE_EVENTS_STREAM_KEY: last_id},
            count=count,
            block=block_ms if block_ms > 0 else None,
        )

        items: list[dict] = []
        next_last_id = last_id

        for _stream_name, messages in streams or []:
            for msg_id, fields in messages:
                decoded = {}
                for k, v in dict(fields).items():
                    key = k.decode() if isinstance(k, (bytes, bytearray)) else str(k)
                    val = v.decode() if isinstance(v, (bytes, bytearray)) else v
                    decoded[key] = val

                items.append({"id": msg_id, **decoded})
                next_last_id = msg_id

        return {"status": "success", "items": items, "next_last_id": next_last_id}

    async def get_payment_progress(self, *, redis, reference: str) -> dict:
        key = f"{PAYMENT_PROGRESS_KEY_PREFIX}{reference}"
        value = await redis.get(key)
        if not value:
            raise NotFoundException("Payment progress not found (or expired)")
        if isinstance(value, (bytes, bytearray)):
            value = value.decode()
        try:
            data = json.loads(value)
        except Exception:
            data = {"raw": value}
        return {"status": "success", "data": data}

    async def get_unread_summary(
        self, *, db, user_id: str, page_size: int = 20
    ) -> dict:
        unread_stmt = (
            select(
                Message.conversation_id, func.count(Message.id).label("unread_count")
            )
            .where(Message.recipient_id == user_id, Message.read_at.is_(None))
            .group_by(Message.conversation_id)
        )
        unread_rows = list((await db.execute(unread_stmt)).all())
        unread_by_conv = {str(cid): int(cnt) for cid, cnt in unread_rows}
        conv_ids = list(unread_by_conv.keys())

        conversations: list[Conversation] = []
        last_by_conversation_id: dict[str, Message] = {}
        if conv_ids:
            conv_result = await db.execute(
                select(Conversation)
                .where(Conversation.id.in_(conv_ids))
                .order_by(Conversation.last_message_at.desc())
            )
            conversations = list(conv_result.scalars().all())

            last_stmt = (
                select(Message)
                .where(Message.conversation_id.in_(conv_ids))
                .order_by(Message.conversation_id, Message.created_at.desc())
                .distinct(Message.conversation_id)
            )
            last_result = await db.execute(last_stmt)
            last_msgs = list(last_result.scalars().all())
            last_by_conversation_id = {str(m.conversation_id): m for m in last_msgs}

        notif_count_stmt = (
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.read_at.is_(None),
                Notification.is_deleted.is_(False),
            )
        )
        notifications_unread = int((await db.execute(notif_count_stmt)).scalar() or 0)

        notif_list_stmt = (
            select(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.read_at.is_(None),
                Notification.is_deleted.is_(False),
            )
            .order_by(Notification.created_at.desc())
            .limit(page_size)
        )
        notif_rows = list((await db.execute(notif_list_stmt)).scalars().all())

        conv_items: list[dict] = []
        for conv in conversations:
            conv_data = chat_service._serialize_conversation(
                conv, current_user_id=user_id
            )
            last = last_by_conversation_id.get(str(conv.id))
            conv_data["last_message"] = last.to_dict() if last is not None else False
            conv_data["unread_count"] = unread_by_conv.get(str(conv.id), 0)
            conv_items.append(conv_data)

        return {
            "notifications": {
                "unread_count": notifications_unread,
                "items": [n.to_dict() for n in notif_rows],
            },
            "chats": {
                "unread_conversations": len(conv_items),
                "items": conv_items,
            },
        }

    async def _publish_presence(self, *, redis, user_id: str, online: bool) -> None:
        async with get_async_session() as db:
            partner_ids = await chat_service.get_conversation_partner_ids(
                db=db, user_id=str(user_id)
            )
            me = await User.get_by_id(str(user_id), db)

        payload = json.dumps(
            {
                "type": "user.online",
                "data": {
                    "user": {
                        "id": str(me.id),
                        "username": me.username,
                        "full_name": me.full_name,
                        "profile_pic": chat_service._serialize_profile_pic(me),
                    },
                    "online": online,
                },
            }
        )
        for pid in partner_ids:
            await redis.publish(f"chat:user:{pid}", payload)
        await redis.publish(f"chat:user:{user_id}", payload)

    async def _presence_heartbeat(self, *, redis, user_id: str) -> None:
        try:
            key = f"{PRESENCE_KEY_PREFIX}{user_id}"
            while True:
                await redis.set(key, "1", ex=PRESENCE_TTL_SECONDS)
                await asyncio.sleep(max(PRESENCE_TTL_SECONDS // 2, 10))
        except Exception:
            return

    async def _send_presence_snapshot(
        self,
        *,
        websocket: WebSocket,
        redis,
        user_id: str,
        send_lock: asyncio.Lock | None = None,
    ) -> None:
        async with get_async_session() as db:
            partner_ids = await chat_service.get_conversation_partner_ids(
                db=db, user_id=str(user_id)
            )
            partner_id_list = sorted({str(pid) for pid in partner_ids})
            users_by_id: dict[str, User] = {}
            if partner_id_list:
                users_result = await db.execute(
                    select(User).where(User.id.in_(partner_id_list))
                )
                users_by_id = {str(u.id): u for u in users_result.scalars().all()}

        keys = [f"{PRESENCE_KEY_PREFIX}{pid}" for pid in partner_id_list]
        values = await redis.mget(*keys) if keys else []
        items: list[dict] = []
        for pid, val in zip(partner_id_list, values, strict=False):
            u = users_by_id.get(pid)
            if u is None:
                continue
            items.append(
                {
                    "user": {
                        "id": str(u.id),
                        "username": u.username,
                        "full_name": u.full_name,
                        "profile_pic": chat_service._serialize_profile_pic(u),
                    },
                    "online": bool(val),
                }
            )
        if not await self._send_json_safe(
            websocket,
            {"type": "user.online.snapshot", "data": {"items": items}},
            send_lock=send_lock,
        ):
            return

    async def _forward_pubsub(
        self,
        *,
        websocket: WebSocket,
        pubsub,
        redis,
        user_id: str,
        send_lock: asyncio.Lock | None = None,
    ) -> None:
        try:
            async for msg in pubsub.listen():
                if msg is None:
                    continue
                if msg.get("type") != "message":
                    continue
                data = msg.get("data")
                if isinstance(data, (bytes, bytearray)):
                    data = data.decode()
                try:
                    parsed_data = json.loads(data)
                except Exception:
                    if not await self._send_text_safe(
                        websocket, str(data), send_lock=send_lock
                    ):
                        return
                    continue
                if str(
                    parsed_data.get("type") or ""
                ) == "chat.message" and not await self._should_deliver_chat_message(
                    redis=redis, user_id=user_id, payload=parsed_data
                ):
                    print(
                        f"[mobile_events] pubsub chat.message skipped -> {user_id}",
                        flush=True,
                    )
                    continue
                if not await self._send_json_safe(
                    websocket, parsed_data, send_lock=send_lock
                ):
                    print(
                        f"[mobile_events] pubsub send failed -> {user_id}", flush=True
                    )
                    return
                print(
                    f"[mobile_events] pubsub chat.message sent -> {user_id}", flush=True
                )
        except Exception:
            return

    async def _forward_chat_stream(
        self,
        *,
        websocket: WebSocket,
        redis,
        user_id: str,
        ready_event: asyncio.Event | None = None,
        send_lock: asyncio.Lock | None = None,
    ) -> None:
        stream_key = f"{CHAT_EVENTS_STREAM_KEY_PREFIX}{user_id}"
        last_id_key = f"{CHAT_EVENTS_LAST_ID_KEY_PREFIX}{user_id}"
        last_id = await redis.get(last_id_key)
        if isinstance(last_id, (bytes, bytearray)):
            last_id = last_id.decode()
        if not last_id:
            latest_entries = await redis.xrevrange(stream_key, count=1)
            last_id = str(latest_entries[0][0]) if latest_entries else "0-0"

        if ready_event is not None:
            ready_event.set()

        try:
            while True:
                streams = await redis.xread(
                    streams={stream_key: last_id}, count=50, block=25000
                )
                for _stream_name, messages in streams or []:
                    for msg_id, fields in messages:
                        event_type = fields.get("type")
                        payload_raw = fields.get("data")
                        if isinstance(event_type, (bytes, bytearray)):
                            event_type = event_type.decode()
                        if isinstance(payload_raw, (bytes, bytearray)):
                            payload_raw = payload_raw.decode()
                        if str(event_type or "") != "chat.message" or not payload_raw:
                            continue
                        payload_obj = None
                        try:
                            payload_obj = json.loads(payload_raw)
                        except Exception:
                            payload_obj = None
                        if payload_obj is None:
                            continue
                        last_id = msg_id
                        await redis.set(
                            last_id_key, last_id, ex=PRESENCE_TTL_SECONDS * 8
                        )
                        if not await self._should_deliver_chat_message(
                            redis=redis, user_id=user_id, payload=payload_obj
                        ):
                            print(
                                f"[mobile_events] stream chat.message skipped -> {user_id}",
                                flush=True,
                            )
                            continue
                        if not await self._send_json_safe(
                            websocket, payload_obj, send_lock=send_lock
                        ):
                            print(
                                f"[mobile_events] stream send failed -> {user_id}",
                                flush=True,
                            )
                            return
                        print(
                            f"[mobile_events] stream chat.message sent -> {user_id}",
                            flush=True,
                        )
        except Exception:
            return

    async def _forward_stream(
        self,
        *,
        websocket: WebSocket,
        redis,
        user_id: str,
        send_lock: asyncio.Lock | None = None,
    ) -> None:
        last_id = "$"
        try:
            while True:
                streams = await redis.xread(
                    streams={MOBILE_EVENTS_STREAM_KEY: last_id}, count=50, block=25000
                )
                for _stream_name, messages in streams or []:
                    for msg_id, fields in messages:
                        last_id = msg_id
                        event_name = fields.get("event_name")
                        payload_raw = fields.get("payload")
                        if not event_name or not payload_raw:
                            continue
                        payload_obj = None
                        with contextlib.suppress(Exception):
                            payload_obj = json.loads(payload_raw)
                        if payload_obj is None:
                            continue
                        if str(payload_obj.get("user_id") or "") != str(user_id):
                            continue
                        if not await self._send_json_safe(
                            websocket,
                            {
                                "type": "event",
                                "event_name": event_name,
                                "payload": payload_obj,
                            },
                            send_lock=send_lock,
                        ):
                            return
        except Exception:
            return

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

        redis = await get_redis_client()
        pubsub = redis.pubsub()
        await pubsub.subscribe(f"chat:user:{user_id}")

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
        bootstrap_task = asyncio.create_task(
            self._bootstrap_connection(
                websocket=websocket,
                redis=redis,
                user_id=str(user_id),
                send_lock=send_lock,
            )
        )

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
        stream_task = asyncio.create_task(
            self._forward_stream(
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

                if msg_type == "ping":
                    if not await self._send_model_safe(
                        websocket, PongEvent(), send_lock=send_lock
                    ):
                        break
                    continue

                if msg_type == "chat.send":
                    try:
                        payload = SendMessagePayload.model_validate(incoming)
                    except Exception:
                        if not await self._send_json_safe(
                            websocket,
                            {
                                "type": "error",
                                "error": "invalid_payload",
                                "message": "Expected: {type:'chat.send', recipient_id:'<uuid>', body:'...'}",
                            },
                            send_lock=send_lock,
                        ):
                            break
                        continue

                    async with get_async_session() as db:
                        try:
                            sender = await User.get_by_id(str(user_id), db)
                            result = await chat_service.send_message(
                                db=db,
                                redis=redis,
                                sender=sender,
                                recipient_id=payload.recipient_id,
                                body=payload.body,
                                reply_to_message_id=(
                                    str(payload.reply_to_message_id)
                                    if payload.reply_to_message_id
                                    else None
                                ),
                                commit=True,
                                as_response=False,
                                persist_notification=False,
                                notify_side_effects=False,
                            )
                        except (
                            NotFoundException,
                            ForbiddenException,
                            BadRequestException,
                        ) as e:
                            if not await self._send_json_safe(
                                websocket,
                                {
                                    "type": "error",
                                    "error": "chat.send.failed",
                                    "message": str(e),
                                },
                                send_lock=send_lock,
                            ):
                                break
                            continue

                    if not await self._send_model_safe(
                        websocket,
                        ChatSentEvent(
                            client_id=payload.client_id,
                            data=ChatSentData(
                                conversation_id=str(result["conversation_id"]),
                                message=ChatMessageData.model_validate(
                                    result["message"]
                                ),
                            ),
                        ),
                        send_lock=send_lock,
                    ):
                        break
                    message_data = ChatMessageData.model_validate(result["message"])
                    await self._send_chat_message_direct(
                        redis=redis,
                        recipient_id=str(payload.recipient_id),
                        payload=ChatMessageEvent(data=message_data),
                    )
                    asyncio.create_task(
                        self._dispatch_chat_side_effects(
                            redis=redis,
                            sender=sender,
                            recipient_id=str(payload.recipient_id),
                            conversation_id=result["conversation_id"],
                            message_id=str(message_data.id),
                            body=payload.body or "",
                        )
                    )
                    continue

                if msg_type == "chat.upload_media":
                    try:
                        payload = UploadMediaPayload.model_validate(incoming)
                    except Exception:
                        if not await self._send_json_safe(
                            websocket,
                            {
                                "type": "error",
                                "error": "invalid_payload",
                                "message": "Expected: {type:'chat.upload_media', recipient_id:'<uuid>', media_type:'image|video|file', media_urls:['https://...'], body?:'...'}",
                            },
                            send_lock=send_lock,
                        ):
                            break
                        continue

                    if str(payload.recipient_id) == str(user_id):
                        if not await self._send_json_safe(
                            websocket,
                            {"type": "error", "error": "self_send_not_allowed"},
                            send_lock=send_lock,
                        ):
                            break
                        continue

                    media_type = (payload.media_type or "").strip().lower()
                    if media_type not in {"image", "video", "file"}:
                        if not await self._send_json_safe(
                            websocket,
                            {"type": "error", "error": "invalid_media_type"},
                            send_lock=send_lock,
                        ):
                            break
                        continue

                    urls = [u for u in (payload.media_urls or []) if u]
                    if not urls:
                        if not await self._send_json_safe(
                            websocket,
                            {"type": "error", "error": "missing_media_urls"},
                            send_lock=send_lock,
                        ):
                            break
                        continue
                    if any(not self._is_cloudinary_secure_url(u) for u in urls):
                        if not await self._send_json_safe(
                            websocket,
                            {"type": "error", "error": "invalid_media_urls"},
                            send_lock=send_lock,
                        ):
                            break
                        continue

                    async with get_async_session() as db:
                        try:
                            sender = await User.get_by_id(str(user_id), db)
                            result = await chat_service.send_media_message(
                                db=db,
                                redis=redis,
                                sender=sender,
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
                                commit=True,
                                as_response=False,
                                persist_notification=False,
                                notify_side_effects=False,
                            )
                        except (
                            NotFoundException,
                            ForbiddenException,
                            BadRequestException,
                        ) as e:
                            if not await self._send_json_safe(
                                websocket,
                                {
                                    "type": "error",
                                    "error": "chat.upload_media.failed",
                                    "message": str(e),
                                },
                                send_lock=send_lock,
                            ):
                                break
                            continue

                    if not await self._send_model_safe(
                        websocket,
                        ChatSentEvent(
                            client_id=payload.client_id,
                            data=ChatSentData(
                                conversation_id=str(result["conversation_id"]),
                                message=ChatMessageData.model_validate(
                                    result["message"]
                                ),
                            ),
                        ),
                        send_lock=send_lock,
                    ):
                        break
                    message_data = ChatMessageData.model_validate(result["message"])
                    await self._send_chat_message_direct(
                        redis=redis,
                        recipient_id=str(payload.recipient_id),
                        payload=ChatMessageEvent(data=message_data),
                    )
                    asyncio.create_task(
                        self._dispatch_chat_side_effects(
                            redis=redis,
                            sender=sender,
                            recipient_id=str(payload.recipient_id),
                            conversation_id=result["conversation_id"],
                            message_id=str(message_data.id),
                            body=payload.body or "",
                            media_type=media_type,
                            media_urls=urls,
                            media_name=message_data.media_name,
                        )
                    )
                    continue

                if msg_type == "chat.read":
                    try:
                        payload = MarkConversationReadPayload.model_validate(incoming)
                    except Exception:
                        if not await self._send_json_safe(
                            websocket,
                            {
                                "type": "error",
                                "error": "invalid_payload",
                                "message": "Expected: {type:'chat.read', recipient_id:'<uuid>', message_id:'<uuid>', mark_all?:true|false}",
                            },
                            send_lock=send_lock,
                        ):
                            break
                        continue

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
                            if not await self._send_json_safe(
                                websocket,
                                {
                                    "type": "error",
                                    "error": "chat.read.failed",
                                    "message": str(e),
                                },
                                send_lock=send_lock,
                            ):
                                break
                            continue

                    if not await self._send_model_safe(
                        websocket,
                        ChatReadAckEvent(data=ChatReadAckData.model_validate(result)),
                        send_lock=send_lock,
                    ):
                        break
                    continue

                if msg_type == "chat.typing":
                    try:
                        payload = TypingPayload.model_validate(incoming)
                    except Exception:
                        if not await self._send_json_safe(
                            websocket,
                            {
                                "type": "error",
                                "error": "invalid_payload",
                                "message": "Expected: {type:'chat.typing', user_id:'<uuid>', is_typing:true|false}",
                            },
                            send_lock=send_lock,
                        ):
                            break
                        continue

                    async with get_async_session() as db:
                        try:
                            conv = await Conversation.get_between(
                                db,
                                uuid.UUID(str(user_id)),
                                uuid.UUID(str(payload.user_id)),
                            )
                            if conv is None:
                                raise NotFoundException("Conversation not found")

                            sender = await User.get_by_id(str(user_id), db)
                            targets = {str(conv.user_a_id), str(conv.user_b_id)}
                        except (
                            NotFoundException,
                            ForbiddenException,
                            BadRequestException,
                        ) as e:
                            if not await self._send_json_safe(
                                websocket,
                                {
                                    "type": "error",
                                    "error": "chat.typing.failed",
                                    "message": str(e),
                                },
                                send_lock=send_lock,
                            ):
                                break
                            continue

                    event_payload = ChatTypingEvent(
                        data=ChatTypingData(
                            conversation_id=str(conv.id),
                            user=ChatUserLite(
                                id=sender.id,
                                username=sender.username,
                                full_name=sender.full_name,
                                profile_pic=chat_service._serialize_profile_pic(sender),
                            ),
                            is_typing=bool(payload.is_typing),
                        )
                    )
                    for target_id in targets:
                        await redis.publish(
                            f"chat:user:{target_id}", event_payload.model_dump_json()
                        )

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
            stream_task.cancel()
            chat_queue_task.cancel()
            presence_task.cancel()
            await asyncio.gather(
                bootstrap_task,
                pubsub_task,
                chat_stream_task,
                stream_task,
                chat_queue_task,
                presence_task,
                return_exceptions=True,
            )
            await pubsub.unsubscribe(f"chat:user:{user_id}")
            await pubsub.close()
            with contextlib.suppress(Exception):
                await redis.delete(f"{PRESENCE_KEY_PREFIX}{user_id}")
                await self._publish_presence(
                    redis=redis, user_id=str(user_id), online=False
                )


mobile_events_service = MobileEventsService()
