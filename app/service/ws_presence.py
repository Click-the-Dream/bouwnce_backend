"""Presence mixin — bootstrap, presence, forwarders, heartbeat, snapshot.

Extracted from mobile_events_service.py to keep file sizes manageable (~500 lines).
"""

from __future__ import annotations

import asyncio
import contextlib
import json

from fastapi import WebSocket

from app.core.config import (
    CHAT_EVENTS_LAST_ID_KEY_PREFIX,
    CHAT_EVENTS_STREAM_KEY_PREFIX,
    MOBILE_EVENTS_STREAM_KEY,
    PAYMENT_PROGRESS_KEY_PREFIX,
)
from app.db.postgres_db_conn import get_async_session
from app.matching_ground.schema.chat import ChatMessageEvent, ChatUserLite
from app.matching_ground.service.bouwnce_dm_service import bouwnce_dm_service
from app.matching_ground.service.chat_service import chat_service
from app.models.chat import Conversation, Message
from app.models.user import User
from app.service.ws_chat import (
    ACTIVE_CHAT_CONNECTIONS,
    ChatDelivery,
)
from app.utils.exception import NotFoundException

PRESENCE_KEY_PREFIX = "presence:user:"
PRESENCE_TTL_SECONDS = 75


class PresenceManager:
    """Bootstrap, presence, and stream-forwarding logic."""

    # ------------------------------------------------------------------
    # Bootstrap
    # ------------------------------------------------------------------
    async def _bootstrap_connection(
        self,
        *,
        websocket: WebSocket,
        redis,
        user_id: str,
        send_lock: asyncio.Lock,
    ) -> None:
        system_user: User | None = None
        partner_ids: set[str] = set()
        me_user: User | None = None
        try:
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

                await bouwnce_dm_service.ensure_welcome_conversation(
                    db=db,
                    redis=redis,
                    user_id=str(user_id),
                    commit=True,
                    system_user=system_user,
                )

                partner_ids = await chat_service.get_conversation_partner_ids(
                    db=db, user_id=str(user_id)
                )
                users = await User.get_chat_users_by_ids([str(user_id)], db)
                me_user = users[0] if users else None
        except Exception as e:
            print(f"[bootstrap] DB phase failed: {type(e).__name__}: {e}", flush=True)

        await redis.set(f"{PRESENCE_KEY_PREFIX}{user_id}", "1", ex=PRESENCE_TTL_SECONDS)

        publish_task = asyncio.create_task(
            self._publish_presence_from_data(
                redis=redis,
                user_id=str(user_id),
                me_user=me_user,
                partner_ids=partner_ids,
                online=True,
            )
        )

        with contextlib.suppress(Exception):
            await self._send_presence_snapshot(
                websocket=websocket,
                redis=redis,
                user_id=str(user_id),
                send_lock=send_lock,
            )
        with contextlib.suppress(Exception):
            await publish_task

    # ------------------------------------------------------------------
    # Presence publish / snapshot
    # ------------------------------------------------------------------
    async def _publish_presence_from_data(
        self,
        *,
        redis,
        me_user: User | None,
        partner_ids: set[str],
        online: bool,
    ) -> None:
        """Publish presence using pre-fetched data (no DB session)."""
        if me_user is None:
            return

        payload_obj = {
            "type": "user.online",
            "data": {
                "user": {
                    "id": str(me_user.id),
                    "username": me_user.username,
                    "full_name": me_user.full_name,
                    "profile_pic": chat_service._serialize_profile_pic(me_user),
                },
                "online": online,
            },
        }
        payload = json.dumps(payload_obj)

        if not partner_ids:
            return

        async with redis.pipeline() as pipe:
            for pid in partner_ids:
                pipe.publish(f"chat:user:{pid}", payload)
            await pipe.execute()

    async def _send_presence_snapshot_from_data(
        self,
        *,
        websocket: WebSocket,
        redis,
        partner_ids: set[str],
        send_lock: asyncio.Lock | None = None,
    ) -> None:
        """Send presence snapshot using pre-fetched partner IDs."""
        partner_id_list = sorted(partner_ids)
        users_by_id: dict[str, User] = {}
        if partner_id_list:
            async with get_async_session() as db:
                users = await User.get_chat_users_by_ids(partner_id_list, db)
                users_by_id = {str(u.id): u for u in users}

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
        await self._send_json_safe(
            websocket,
            {"type": "user.online.snapshot", "data": {"items": items}},
            send_lock=send_lock,
        )

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
                users = await User.get_chat_users_by_ids(partner_id_list, db)
                users_by_id = {str(u.id): u for u in users}

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
        await self._send_json_safe(
            websocket,
            {"type": "user.online.snapshot", "data": {"items": items}},
            send_lock=send_lock,
        )

    async def _publish_presence(self, *, redis, user_id: str, online: bool) -> None:
        async with get_async_session() as db:
            partner_ids = await chat_service.get_conversation_partner_ids(
                db=db, user_id=str(user_id)
            )
            users = await User.get_chat_users_by_ids([str(user_id)], db)
            me = users[0] if users else None
            if me is None:
                return

        payload_obj = {
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
        payload = json.dumps(payload_obj)

        for pid in {*partner_ids, str(user_id)}:
            connections = ACTIVE_CHAT_CONNECTIONS.get(str(pid)) or {}
            for _connection_id, (
                websocket,
                send_lock,
                _chat_queue,
            ) in connections.items():
                with contextlib.suppress(Exception):
                    await self._send_json_safe(
                        websocket, payload_obj, send_lock=send_lock
                    )

        try:
            async with redis.pipeline() as pipe:
                for pid in partner_ids:
                    pipe.publish(f"chat:user:{pid}", payload)
                pipe.publish(f"chat:user:{user_id}", payload)
                await pipe.execute()
        except Exception:
            return

    # ------------------------------------------------------------------
    # Heartbeat
    # ------------------------------------------------------------------
    async def _presence_heartbeat(self, *, redis, user_id: str) -> None:
        try:
            key = f"{PRESENCE_KEY_PREFIX}{user_id}"
            while True:
                await redis.set(key, "1", ex=PRESENCE_TTL_SECONDS)
                await asyncio.sleep(max(PRESENCE_TTL_SECONDS // 2, 10))
        except Exception:
            return

    # ------------------------------------------------------------------
    # Redis stream forwarders
    # ------------------------------------------------------------------
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
                    continue
                if not await self._send_json_safe(
                    websocket, parsed_data, send_lock=send_lock
                ):
                    return
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
                            continue
                        if not await self._send_json_safe(
                            websocket, payload_obj, send_lock=send_lock
                        ):
                            return
        except Exception:
            return

    # ------------------------------------------------------------------
    # Mobile events / payment progress / unread summary
    # ------------------------------------------------------------------
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
        from sqlalchemy import func, select

        from app.matching_ground.model.notification import Notification

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

        users_by_id: dict[str, User] = {}
        if conversations:
            users_by_id = await chat_service._load_users_for_conversations(
                db, conversations
            )

        conv_items: list[dict] = []
        for conv in conversations:
            conv_data = chat_service._serialize_conversation(
                conv, current_user_id=user_id, users_by_id=users_by_id
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
