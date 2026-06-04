from __future__ import annotations

import asyncio
import contextlib
import json
import uuid

from fastapi import WebSocket
from sqlalchemy import func, select
from starlette.websockets import WebSocketDisconnect

from app.core.config import (
    MOBILE_EVENTS_STREAM_KEY,
    PAYMENT_PROGRESS_KEY_PREFIX,
    settings,
)
from app.core.security import verify_token
from app.db.postgres_db_conn import get_async_session
from app.db.redis import get_redis_client
from app.matching_ground.model.notification import Notification
from app.matching_ground.schema.chat import (
    MarkConversationReadPayload,
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

PRESENCE_KEY_PREFIX = "presence:user:"
PRESENCE_TTL_SECONDS = 75


class MobileEventsService:
    @staticmethod
    def _is_cloudinary_secure_url(url: str) -> bool:
        if not url:
            return False
        prefix = f"https://res.cloudinary.com/{settings.CLOUDINARY_NAME}/"
        return str(url).startswith(prefix)

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
        self, *, websocket: WebSocket, redis, user_id: str
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
        await websocket.send_json(
            {"type": "user.online.snapshot", "data": {"items": items}}
        )

    async def _forward_pubsub(self, *, websocket: WebSocket, pubsub) -> None:
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
                    await websocket.send_json(json.loads(data))
                except Exception:
                    await websocket.send_text(str(data))
        except Exception:
            return

    async def _forward_stream(
        self, *, websocket: WebSocket, redis, user_id: str
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
                        await websocket.send_json(
                            {
                                "type": "event",
                                "event_name": event_name,
                                "payload": payload_obj,
                            }
                        )
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

        # Tell client who the Bouwnce system user is (for disabling replies in UI).
        with contextlib.suppress(Exception):
            async with get_async_session() as db:
                system_user = await bouwnce_dm_service.get_system_user(db=db)
                if system_user is not None:
                    await websocket.send_json(
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
                        }
                    )

        # Ensure Bouwnce inbox conversation exists with welcome message
        with contextlib.suppress(Exception):
            async with get_async_session() as db:
                await bouwnce_dm_service.ensure_welcome_conversation(
                    db=db, redis=redis, user_id=str(user_id), commit=True
                )

        await redis.set(f"{PRESENCE_KEY_PREFIX}{user_id}", "1", ex=PRESENCE_TTL_SECONDS)
        await self._publish_presence(redis=redis, user_id=str(user_id), online=True)

        with contextlib.suppress(Exception):
            await self._send_presence_snapshot(
                websocket=websocket, redis=redis, user_id=str(user_id)
            )

        pubsub_task = asyncio.create_task(
            self._forward_pubsub(websocket=websocket, pubsub=pubsub)
        )
        stream_task = asyncio.create_task(
            self._forward_stream(websocket=websocket, redis=redis, user_id=str(user_id))
        )
        presence_task = asyncio.create_task(
            self._presence_heartbeat(redis=redis, user_id=str(user_id))
        )

        try:
            while True:
                try:
                    raw = await websocket.receive_text()
                except (WebSocketDisconnect, RuntimeError):
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
                    await websocket.send_json({"type": "pong"})
                    continue

                if msg_type == "chat.send":
                    try:
                        payload = SendMessagePayload.model_validate(incoming)
                    except Exception:
                        await websocket.send_json(
                            {
                                "type": "error",
                                "error": "invalid_payload",
                                "message": "Expected: {type:'chat.send', recipient_id:'<uuid>', body:'...'}",
                            }
                        )
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
                                commit=False,
                                as_response=False,
                            )
                        except (
                            NotFoundException,
                            ForbiddenException,
                            BadRequestException,
                        ) as e:
                            await websocket.send_json(
                                {
                                    "type": "error",
                                    "error": "chat.send.failed",
                                    "message": str(e),
                                }
                            )
                            continue

                    await websocket.send_json(
                        {
                            "type": "chat.sent",
                            "client_id": payload.client_id,
                            "data": {**result},
                        }
                    )
                    continue

                if msg_type == "chat.upload_media":
                    try:
                        payload = UploadMediaPayload.model_validate(incoming)
                    except Exception:
                        await websocket.send_json(
                            {
                                "type": "error",
                                "error": "invalid_payload",
                                "message": "Expected: {type:'chat.upload_media', recipient_id:'<uuid>', media_type:'image|video|file', media_urls:['https://...'], body?:'...'}",
                            }
                        )
                        continue

                    if str(payload.recipient_id) == str(user_id):
                        await websocket.send_json(
                            {"type": "error", "error": "self_send_not_allowed"}
                        )
                        continue

                    media_type = (payload.media_type or "").strip().lower()
                    if media_type not in {"image", "video", "file"}:
                        await websocket.send_json(
                            {"type": "error", "error": "invalid_media_type"}
                        )
                        continue

                    urls = [u for u in (payload.media_urls or []) if u]
                    if not urls:
                        await websocket.send_json(
                            {"type": "error", "error": "missing_media_urls"}
                        )
                        continue
                    if any(not self._is_cloudinary_secure_url(u) for u in urls):
                        await websocket.send_json(
                            {"type": "error", "error": "invalid_media_urls"}
                        )
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
                                commit=False,
                                as_response=False,
                            )
                        except (
                            NotFoundException,
                            ForbiddenException,
                            BadRequestException,
                        ) as e:
                            await websocket.send_json(
                                {
                                    "type": "error",
                                    "error": "chat.upload_media.failed",
                                    "message": str(e),
                                }
                            )
                            continue

                    await websocket.send_json(
                        {
                            "type": "chat.sent",
                            "client_id": payload.client_id,
                            "data": {**result},
                        }
                    )
                    continue

                if msg_type == "chat.read":
                    try:
                        payload = MarkConversationReadPayload.model_validate(incoming)
                    except Exception:
                        await websocket.send_json(
                            {
                                "type": "error",
                                "error": "invalid_payload",
                                "message": "Expected: {type:'chat.read', recipient_id:'<uuid>', message_id:'<uuid>', mark_all?:true|false}",
                            }
                        )
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
                            await websocket.send_json(
                                {
                                    "type": "error",
                                    "error": "chat.read.failed",
                                    "message": str(e),
                                }
                            )
                            continue

                    await websocket.send_json({"type": "chat.read.ack", "data": result})
                    continue

                if msg_type == "chat.typing":
                    try:
                        payload = TypingPayload.model_validate(incoming)
                    except Exception:
                        await websocket.send_json(
                            {
                                "type": "error",
                                "error": "invalid_payload",
                                "message": "Expected: {type:'chat.typing', user_id:'<uuid>', is_typing:true|false}",
                            }
                        )
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
                            await websocket.send_json(
                                {
                                    "type": "error",
                                    "error": "chat.typing.failed",
                                    "message": str(e),
                                }
                            )
                            continue

                    event_payload = json.dumps(
                        {
                            "type": "chat.typing",
                            "data": {
                                "conversation_id": str(conv.id),
                                "user": {
                                    "id": str(sender.id),
                                    "username": sender.username,
                                    "full_name": sender.full_name,
                                    "profile_pic": chat_service._serialize_profile_pic(
                                        sender
                                    ),
                                },
                                "is_typing": bool(payload.is_typing),
                            },
                        }
                    )
                    for target_id in targets:
                        await redis.publish(f"chat:user:{target_id}", event_payload)

                    await websocket.send_json(
                        {
                            "type": "chat.typing.ack",
                            "data": {
                                "conversation_id": str(conv.id),
                                "user_id": str(payload.user_id),
                                "is_typing": bool(payload.is_typing),
                            },
                        }
                    )
                    continue
        finally:
            pubsub_task.cancel()
            stream_task.cancel()
            presence_task.cancel()
            await pubsub.unsubscribe(f"chat:user:{user_id}")
            await pubsub.close()
            with contextlib.suppress(Exception):
                await redis.delete(f"{PRESENCE_KEY_PREFIX}{user_id}")
                await self._publish_presence(
                    redis=redis, user_id=str(user_id), online=False
                )


mobile_events_service = MobileEventsService()
