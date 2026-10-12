"""
Group Chat WebSocket Service

Delivery model mirrors the direct-message chat (``ws_chat`` / ``ws_presence``):

- One shared ``group_pubsub_dispatcher`` does a single ``psubscribe`` for
  ``group:user:*`` and fans messages out across workers.
- Every group message is also appended to a per-group Redis Stream so a
  reconnecting client can catch up on anything it missed while offline.
- Fan-out is deduplicated per ``(user, message)`` both in-process and in Redis,
  so a message is delivered at most once no matter which path (direct socket,
  pub/sub, catch-up) wins the race.
- Members who are offline still receive a push/mobile event (mirroring
  ``_dispatch_chat_side_effects`` in the DM path).
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import time
import uuid
from typing import Any

from fastapi import WebSocket
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.websockets import WebSocketDisconnect
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK

from app.core.logger import logger
from app.core.security import verify_token
from app.db.postgres_db_conn import get_async_session
from app.db.redis import get_redis_client
from app.matching_ground.model.notification import Notification
from app.models.user import User
from app.service import group_service
from app.service.ws_presence import PubSubDispatcher
from app.worker.event_system import (
    EventNames,
    MobileEvent,
    PushNotificationEvent,
    dispatch_event,
)

# ---------------------------------------------------------------------------
# Redis keys / channels for cross-worker group chat delivery
# ---------------------------------------------------------------------------
GROUP_CHANNEL_PREFIX = "group:user:"
GROUP_EVENTS_STREAM_KEY_PREFIX = "group:events:stream:"
GROUP_EVENTS_LAST_ID_KEY_PREFIX = "group:events:last:"
GROUP_DELIVERED_KEY_PREFIX = "group:delivered:"
GROUP_STREAM_EVENT_TYPE = "group.message"
GROUP_STREAM_MAXLEN = 5000
GROUP_DELIVERED_TTL_SECONDS = 30 * 24 * 60 * 60  # 30 days
GROUP_LOCAL_DELIVERY_TTL_SECONDS = 300.0

# One dispatcher per app instance for group channels.  Kept separate from the
# DM chat dispatcher so a group frame is never delivered to a chat socket (and
# vice versa) when the same user has both open.
group_pubsub_dispatcher = PubSubDispatcher(patterns=("group:user:*",))

# In-process dedup so the direct broadcast path and the pub/sub path do not
# deliver the same frame twice.
_ACTIVE_GROUP_LOCAL_DELIVERIES: dict[str, float] = {}


class GroupConnectionManager:
    """Tracks the group WebSocket connections owned by this worker."""

    def __init__(self) -> None:
        # {group_id: {connection_id: websocket}}
        self.active_connections: dict[str, dict[str, WebSocket]] = {}
        # {connection_id: user_id}
        self.connection_users: dict[str, str] = {}
        # {connection_id: group_id}
        self.connection_groups: dict[str, str] = {}
        # {user_id: {group_id}}
        self.user_groups: dict[str, set[str]] = {}

    def connect(
        self, websocket: WebSocket, group_id: str, user_id: str, connection_id: str
    ) -> None:
        """Register an already-accepted WebSocket for a group."""
        self.active_connections.setdefault(group_id, {})[connection_id] = websocket
        self.connection_users[connection_id] = user_id
        self.connection_groups[connection_id] = group_id
        self.user_groups.setdefault(user_id, set()).add(group_id)
        logger.info(
            "User %s connected to group %s (connection %s)",
            user_id,
            group_id,
            connection_id,
        )

    def disconnect(self, connection_id: str) -> None:
        """Remove a connection and clean up empty group/user entries."""
        group_id = self.connection_groups.pop(connection_id, None)
        user_id = self.connection_users.pop(connection_id, None)
        if group_id is not None:
            connections = self.active_connections.get(group_id)
            if connections is not None:
                connections.pop(connection_id, None)
                if not connections:
                    self.active_connections.pop(group_id, None)
        if user_id is not None:
            groups = self.user_groups.get(user_id)
            if groups is not None:
                groups.discard(group_id or "")
                if not groups:
                    self.user_groups.pop(user_id, None)
        if group_id is not None:
            logger.info(
                "User %s disconnected from group %s (connection %s)",
                user_id,
                group_id,
                connection_id,
            )

    def connections_for_group(self, group_id: str) -> dict[str, WebSocket]:
        return dict(self.active_connections.get(group_id, {}))

    def local_member_ids(self, group_id: str) -> set[str]:
        return {
            self.connection_users[cid]
            for cid in self.active_connections.get(group_id, {})
            if cid in self.connection_users
        }

    def get_group_connections(self, group_id: str) -> int:
        return len(self.active_connections.get(group_id, {}))


# Global connection manager instance (this worker only)
group_connection_manager = GroupConnectionManager()


# ---------------------------------------------------------------------------
# Safe send helpers
# ---------------------------------------------------------------------------
async def _send_json_safe(
    websocket: WebSocket,
    payload: dict,
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


# ---------------------------------------------------------------------------
# Delivery dedup (in-process + Redis)
# ---------------------------------------------------------------------------
def _claim_local_group_delivery(delivered_key: str) -> bool:
    now = time.monotonic()
    if len(_ACTIVE_GROUP_LOCAL_DELIVERIES) > 10000:
        expired = [
            key
            for key, expires_at in _ACTIVE_GROUP_LOCAL_DELIVERIES.items()
            if expires_at <= now
        ]
        for key in expired:
            _ACTIVE_GROUP_LOCAL_DELIVERIES.pop(key, None)

    expires_at = _ACTIVE_GROUP_LOCAL_DELIVERIES.get(delivered_key)
    if expires_at is not None and expires_at > now:
        return False
    _ACTIVE_GROUP_LOCAL_DELIVERIES[delivered_key] = (
        now + GROUP_LOCAL_DELIVERY_TTL_SECONDS
    )
    return True


def _group_delivered_key(user_id: str, message_id: str) -> str:
    return f"{GROUP_DELIVERED_KEY_PREFIX}{user_id}:{message_id}"


def _payload_message_id(payload: dict) -> str | None:
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, dict):
        return None
    message_id = str(data.get("id") or "").strip()
    return message_id or None


async def _claim_group_delivery(redis, user_id: str, message_id: str) -> bool:
    """Claim the right to deliver ``message_id`` to ``user_id``."""
    delivered_key = _group_delivered_key(user_id, message_id)
    if not _claim_local_group_delivery(delivered_key):
        return False
    with contextlib.suppress(Exception):
        return bool(
            await redis.set(
                delivered_key,
                "1",
                ex=GROUP_DELIVERED_TTL_SECONDS,
                nx=True,
            )
        )
    return True


async def _release_group_delivery(redis, user_id: str, message_id: str) -> None:
    delivered_key = _group_delivered_key(user_id, message_id)
    _ACTIVE_GROUP_LOCAL_DELIVERIES.pop(delivered_key, None)
    with contextlib.suppress(Exception):
        await redis.delete(delivered_key)


async def deliver_group_payload(
    *,
    redis,
    websocket: WebSocket,
    payload: dict,
    user_id: str,
    send_lock: asyncio.Lock | None = None,
) -> bool:
    """Deliver one fan-out frame to a socket, deduplicating message frames.

    Used both for direct in-worker delivery and as the pub/sub send callback,
    so whichever path arrives first wins and the other is a no-op.
    """
    message_id = _payload_message_id(payload)
    if message_id is not None and not await _claim_group_delivery(
        redis, user_id, message_id
    ):
        return False

    sent = await _send_json_safe(websocket, payload, send_lock)
    if not sent and message_id is not None:
        # Send failed: release the claim so a retry / catch-up can deliver it.
        await _release_group_delivery(redis, user_id, message_id)
    return sent


# ---------------------------------------------------------------------------
# Fan-out
# ---------------------------------------------------------------------------
async def _deliver_to_local_connections(
    *,
    redis,
    group_id: str,
    payload: dict,
) -> None:
    """Deliver a frame to every connection this worker holds for the group."""
    for connection_id, websocket in group_connection_manager.connections_for_group(
        group_id
    ).items():
        user_id = group_connection_manager.connection_users.get(connection_id)
        if user_id is None:
            continue
        await deliver_group_payload(
            redis=redis,
            websocket=websocket,
            payload=payload,
            user_id=user_id,
        )


async def _fanout_group_message(
    *,
    redis,
    group_id: str,
    sender_id: str,
    message_id: str,
    payload: dict,
    member_ids: list[str],
) -> None:
    """Deliver a group message locally, then fan it out to the other workers."""
    # 1) Direct delivery on this worker.
    await _deliver_to_local_connections(redis=redis, group_id=group_id, payload=payload)

    # 2) Pub/sub for connections on other workers + stream for catch-up.
    payload_json = json.dumps(payload)
    with contextlib.suppress(Exception):
        async with redis.pipeline() as pipe:
            for member_id in member_ids:
                pipe.publish(f"{GROUP_CHANNEL_PREFIX}{member_id}", payload_json)
            pipe.xadd(
                f"{GROUP_EVENTS_STREAM_KEY_PREFIX}{group_id}",
                {"type": GROUP_STREAM_EVENT_TYPE, "data": payload_json},
                maxlen=GROUP_STREAM_MAXLEN,
                approximate=True,
            )
            await pipe.execute()


async def _publish_group_frame(*, redis, member_ids: list[str], payload: dict) -> None:
    """Publish a non-persisted frame (e.g. typing) to the given members."""
    payload_json = json.dumps(payload)
    with contextlib.suppress(Exception):
        async with redis.pipeline() as pipe:
            for member_id in member_ids:
                pipe.publish(f"{GROUP_CHANNEL_PREFIX}{member_id}", payload_json)
            await pipe.execute()


# ---------------------------------------------------------------------------
# Catch-up on reconnect
# ---------------------------------------------------------------------------
async def _catchup_group_stream(
    *,
    websocket: WebSocket,
    redis,
    group_id: str,
    user_id: str,
    send_lock: asyncio.Lock | None = None,
) -> None:
    """One-time non-blocking read of the group stream to replay missed messages."""
    stream_key = f"{GROUP_EVENTS_STREAM_KEY_PREFIX}{group_id}"
    last_id_key = f"{GROUP_EVENTS_LAST_ID_KEY_PREFIX}{group_id}:{user_id}"

    last_id = await redis.get(last_id_key)
    if isinstance(last_id, (bytes, bytearray)):
        last_id = last_id.decode()
    if not last_id:
        # First connect: do not replay the whole history (the client loads that
        # over REST).  Anchor the cursor at the newest entry and persist it, so
        # a later reconnect replays only what arrived after this moment.
        last_id = "0-0"
        with contextlib.suppress(Exception):
            newest = await redis.xrevrange(stream_key, count=1)
            if newest:
                newest_id = newest[0][0]
                last_id = (
                    newest_id.decode()
                    if isinstance(newest_id, (bytes, bytearray))
                    else str(newest_id)
                )
        with contextlib.suppress(Exception):
            await redis.set(last_id_key, last_id, ex=GROUP_DELIVERED_TTL_SECONDS)

    # Non-blocking read — ``block=None`` omits BLOCK entirely and returns
    # immediately (``block=0`` would emit BLOCK 0 and hang forever).
    streams = await redis.xread(streams={stream_key: last_id}, count=100, block=None)

    for _stream_name, messages in streams or []:
        for msg_id, fields in messages:
            event_type = fields.get("type")
            payload_raw = fields.get("data")
            if isinstance(event_type, (bytes, bytearray)):
                event_type = event_type.decode()
            if isinstance(payload_raw, (bytes, bytearray)):
                payload_raw = payload_raw.decode()

            if str(event_type or "") != GROUP_STREAM_EVENT_TYPE or not payload_raw:
                last_id = msg_id
                await redis.set(last_id_key, last_id, ex=GROUP_DELIVERED_TTL_SECONDS)
                continue

            try:
                payload_obj = json.loads(payload_raw)
            except Exception:
                last_id = msg_id
                await redis.set(last_id_key, last_id, ex=GROUP_DELIVERED_TTL_SECONDS)
                continue

            sent = await deliver_group_payload(
                redis=redis,
                websocket=websocket,
                payload=payload_obj,
                user_id=user_id,
                send_lock=send_lock,
            )
            if sent:
                last_id = msg_id
                await redis.set(last_id_key, last_id, ex=GROUP_DELIVERED_TTL_SECONDS)
            else:
                # Either already delivered or the socket is dead — do not
                # advance the cursor so a later reconnect can still replay it.
                return


# ---------------------------------------------------------------------------
# Push / mobile side effects for members (mirrors DM chat)
# ---------------------------------------------------------------------------
def _serialize_user(user: User) -> dict[str, Any]:
    return {
        "id": str(user.id),
        "username": user.username,
        "full_name": user.full_name,
        "profile_pic": getattr(user, "profile_pic", None),
    }


async def _dispatch_group_side_effects(
    *,
    redis,
    group_id: str,
    sender_id: str,
    message_id: str,
    body: str,
    member_ids: list[str],
    media_type: str | None = None,
    media_urls: list[str] | None = None,
    media_names: list[str] | None = None,
) -> None:
    """Persist notifications and enqueue push/mobile events for the members."""
    try:
        async with get_async_session() as db:
            sender = await User.get_by_id(sender_id, db)
            title = "New group message"
            sender_lite: dict[str, Any] | None = None
            if sender is not None:
                title = sender.full_name or sender.username or title
                sender_lite = _serialize_user(sender)

            for member_id in member_ids:
                if str(member_id) == str(sender_id):
                    continue

                push_data: dict[str, Any] = {
                    "type": "group.message.created",
                    "group_id": group_id,
                    "message_id": message_id,
                    "sender_id": str(sender_id),
                    "body": (body or "")[:80],
                }
                if media_type:
                    push_data["media_type"] = media_type
                    push_data["media_urls"] = media_urls or []
                    push_data["media_names"] = media_names or []

                # One durable notification row per member.  The push/mobile
                # dispatches below use a ``group.`` type so ``dispatch_event``
                # does not persist a second copy.
                await Notification.create(
                    data={
                        "user_id": member_id,
                        "title": title,
                        "body": (body or "")[:120],
                        "event_type": "group_message",
                        "payload": {
                            "route": "group.chat",
                            "group_id": group_id,
                            "message_id": message_id,
                            "sender": sender_lite,
                        },
                    },
                    db=db,
                )
                await dispatch_event(
                    EventNames.PUSH_NOTIFICATION,
                    PushNotificationEvent(
                        user_id=str(member_id),
                        title=title,
                        body=(body or "")[:80],
                        data=push_data,
                    ),
                    db=db,
                    redis=redis,
                )
                await dispatch_event(
                    EventNames.MOBILE_EVENT,
                    MobileEvent(
                        event_name="group.message.created",
                        payload={**push_data, "user_id": str(member_id)},
                    ),
                    db=db,
                    redis=redis,
                )
            await db.commit()
    except Exception:
        logger.warning(
            "Failed to dispatch group side effects for group %s",
            group_id,
            exc_info=True,
        )


# ---------------------------------------------------------------------------
# Membership helpers
# ---------------------------------------------------------------------------
async def _active_member_ids(db: AsyncSession, group_id: str) -> list[str]:
    members = await group_service.member_repo.get_group_members(db, group_id)
    return [str(member.user_id) for member in members if member.is_active]


# ---------------------------------------------------------------------------
# WebSocket entrypoint
# ---------------------------------------------------------------------------
async def handle_group_websocket(websocket: WebSocket, token: str) -> None:
    """Handle a group chat WebSocket connection."""
    token_payload = verify_token(token)
    if not token_payload or token_payload.get("type") != "access":
        await websocket.close(code=1008)
        return

    user_id = token_payload.get("sub")
    if not user_id:
        await websocket.close(code=1008)
        return
    user_id = str(user_id)

    group_id = websocket.query_params.get("group_id")
    if not group_id:
        await websocket.close(code=1008)
        return
    group_id = str(group_id)

    # Only active members may open a group socket.
    try:
        async with get_async_session() as db:
            member = await group_service.member_repo.get_member(db, group_id, user_id)
            if not member or not member.is_active:
                await websocket.close(code=1008)
                return
    except Exception:
        await websocket.close(code=1008)
        return

    redis = await get_redis_client()
    await group_pubsub_dispatcher.start(redis)

    await websocket.accept()
    send_lock = asyncio.Lock()
    connection_id = uuid.uuid4().hex
    group_connection_manager.connect(websocket, group_id, user_id, connection_id)

    # Register with the shared group dispatcher so pub/sub fan-out (from other
    # workers) reaches this socket through the single psubscribe connection.
    await group_pubsub_dispatcher.register(
        user_id=user_id,
        connection_id=connection_id,
        send_callback=lambda payload, _lock: deliver_group_payload(
            redis=redis,
            websocket=websocket,
            payload=payload,
            user_id=user_id,
            send_lock=send_lock,
        ),
    )

    with contextlib.suppress(Exception):
        await _catchup_group_stream(
            websocket=websocket,
            redis=redis,
            group_id=group_id,
            user_id=user_id,
            send_lock=send_lock,
        )
    with contextlib.suppress(Exception):
        await _send_json_safe(
            websocket,
            {
                "type": "group.ready",
                "data": {"group_id": group_id, "user_id": user_id},
            },
            send_lock,
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

            try:
                message_data = json.loads(raw)
            except json.JSONDecodeError:
                await _send_json_safe(
                    websocket,
                    {"type": "error", "message": "Invalid JSON format"},
                    send_lock,
                )
                continue
            if not isinstance(message_data, dict):
                await _send_json_safe(
                    websocket,
                    {"type": "error", "message": "Invalid message format"},
                    send_lock,
                )
                continue

            await _process_group_message(
                websocket=websocket,
                redis=redis,
                message_data=message_data,
                user_id=user_id,
                group_id=group_id,
                send_lock=send_lock,
            )
    finally:
        group_connection_manager.disconnect(connection_id)
        with contextlib.suppress(Exception):
            await group_pubsub_dispatcher.unregister(
                user_id=user_id, connection_id=connection_id
            )


async def _process_group_message(
    *,
    websocket: WebSocket,
    redis,
    message_data: dict,
    user_id: str,
    group_id: str,
    send_lock: asyncio.Lock,
) -> None:
    message_type = str(message_data.get("type") or "").strip().lower()

    if message_type in ("group_message", "group.message"):
        await _handle_group_chat_message(
            websocket=websocket,
            redis=redis,
            message_data=message_data,
            user_id=user_id,
            group_id=group_id,
            send_lock=send_lock,
        )
    elif message_type in ("group_typing", "group.typing"):
        await _handle_group_typing(
            websocket=websocket,
            redis=redis,
            message_data=message_data,
            user_id=user_id,
            group_id=group_id,
            send_lock=send_lock,
        )
    elif message_type == "ping":
        await _send_json_safe(websocket, {"type": "pong"}, send_lock)
    else:
        await _send_json_safe(
            websocket,
            {
                "type": "error",
                "message": f"Unknown message type: {message_data.get('type')}",
            },
            send_lock,
        )


async def _handle_group_chat_message(
    *,
    websocket: WebSocket,
    redis,
    message_data: dict,
    user_id: str,
    group_id: str,
    send_lock: asyncio.Lock,
) -> None:
    """Persist, fan out, ack and notify for an incoming ``group_message``."""
    body = str(message_data.get("body", "") or "").strip()
    if not body:
        await _send_json_safe(
            websocket,
            {"type": "error", "message": "Message body cannot be empty"},
            send_lock,
        )
        return

    media_type = message_data.get("media_type")
    media_urls = message_data.get("media_urls")
    media_names = message_data.get("media_names")
    reply_to_message_id = message_data.get("reply_to_message_id")
    mentioned_user_ids = message_data.get("mentioned_user_ids")
    client_id = message_data.get("client_id")

    try:
        async with get_async_session() as db:
            result = await group_service.send_message(
                db=db,
                group_id=group_id,
                sender_id=user_id,
                body=body,
                media_type=media_type,
                media_urls=media_urls,
                media_names=media_names,
                reply_to_message_id=reply_to_message_id,
                mentioned_user_ids=mentioned_user_ids,
            )
            member_ids = await _active_member_ids(db, group_id)
    except Exception as exc:
        logger.warning("Failed to send group message: %s", exc)
        await _send_json_safe(
            websocket,
            {
                "type": "error",
                "error": "group.message.failed",
                "message": str(exc),
            },
            send_lock,
        )
        return

    message = result["data"]["message"]
    message_id = str(message.get("id"))
    frame = {
        "type": "group_message",
        "data": message,
        "sender": result["data"]["sender"],
    }

    await _fanout_group_message(
        redis=redis,
        group_id=group_id,
        sender_id=user_id,
        message_id=message_id,
        payload=frame,
        member_ids=member_ids,
    )

    await _send_json_safe(
        websocket,
        {
            "type": "group_message_sent",
            "client_id": client_id,
            "data": message,
        },
        send_lock,
    )

    # Offline members keep getting notified; this is a no-op for the sender.
    await _dispatch_group_side_effects(
        redis=redis,
        group_id=group_id,
        sender_id=user_id,
        message_id=message_id,
        body=body,
        member_ids=member_ids,
        media_type=media_type,
        media_urls=media_urls,
        media_names=media_names,
    )


async def _handle_group_typing(
    *,
    websocket: WebSocket,
    redis,
    message_data: dict,
    user_id: str,
    group_id: str,
    send_lock: asyncio.Lock,
) -> None:
    """Broadcast a typing indicator to every other member (sender excluded)."""
    is_typing = bool(message_data.get("is_typing", False))
    try:
        async with get_async_session() as db:
            member_ids = await _active_member_ids(db, group_id)
    except Exception:
        return

    frame = {
        "type": "group_typing",
        "data": {
            "group_id": group_id,
            "user_id": user_id,
            "is_typing": is_typing,
        },
    }
    targets = [mid for mid in member_ids if mid != user_id]
    await _publish_group_frame(redis=redis, member_ids=targets, payload=frame)
