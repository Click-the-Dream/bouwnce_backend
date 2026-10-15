"""Group chat actions and delivery over the shared user events socket."""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any

from fastapi import WebSocket
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.websockets import WebSocketDisconnect
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK

from app.core.logger import logger
from app.db.postgres_db_conn import get_async_session
from app.matching_ground.model.notification import Notification
from app.models.chat import GroupMember
from app.models.user import User
from app.schemas.group import GroupMessageUpdate
from app.service import group_service
from app.utils.exception import ForbiddenException
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
# Fan-out
# ---------------------------------------------------------------------------
async def _publish_group_frame(*, redis, member_ids: list[str], payload: dict) -> bool:
    """Publish a frame (message or typing) to the given members' event sockets."""
    payload_json = json.dumps(payload)
    try:
        async with redis.pipeline() as pipe:
            for member_id in member_ids:
                pipe.publish(f"{GROUP_CHANNEL_PREFIX}{member_id}", payload_json)
            await pipe.execute()
        return True
    except Exception:
        logger.exception("Failed to publish group frame to member events sockets")
        return False


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

                # The push/mobile dispatches below use a ``group.`` type so
                # ``dispatch_event`` does not persist a second copy.
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
# Membership and action handling
# ---------------------------------------------------------------------------
async def _active_member_ids(db: AsyncSession, group_id: str) -> list[str]:
    members = await group_service.member_repo.get_group_members(db, group_id)
    return [str(member.user_id) for member in members if member.is_active]


async def process_group_action(
    *,
    websocket: WebSocket,
    redis,
    message_data: dict,
    user_id: str,
    send_lock: asyncio.Lock,
) -> None:
    """Validate group context and handle one action on the events socket."""
    group_id = str(message_data.get("group_id") or "").strip()
    try:
        group_id = str(uuid.UUID(group_id))
    except (ValueError, AttributeError):
        await _send_json_safe(
            websocket,
            {
                "type": "error",
                "error": "invalid_group_id",
                "message": "A valid group_id is required for group actions",
            },
            send_lock,
        )
        return

    await _process_group_action(
        websocket=websocket,
        redis=redis,
        message_data=message_data,
        user_id=user_id,
        group_id=group_id,
        send_lock=send_lock,
    )


async def _process_group_action(
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
    elif message_type in ("group_message_edit", "group_message_delete"):
        await _handle_group_message_mutation(
            websocket=websocket,
            redis=redis,
            message_data=message_data,
            user_id=user_id,
            group_id=group_id,
            message_type=message_type,
            send_lock=send_lock,
        )
    else:
        await _send_json_safe(
            websocket,
            {
                "type": "error",
                "message": f"Unknown message type: {message_data.get('type')}",
            },
            send_lock,
        )


async def _handle_group_message_mutation(
    *,
    websocket: WebSocket,
    redis,
    message_data: dict,
    user_id: str,
    group_id: str,
    message_type: str,
    send_lock: asyncio.Lock,
) -> None:
    message_id = str(message_data.get("message_id") or "").strip()
    try:
        message_id = str(uuid.UUID(message_id))
        async with get_async_session() as db:
            member_ids = await _active_member_ids(db, group_id)
            if user_id not in member_ids:
                raise ForbiddenException("You are not an active member of this group")

            if message_type == "group_message_edit":
                update_data = GroupMessageUpdate.model_validate(message_data)
                fields = ("body", "media_type", "media_urls", "media_names")
                if not any(getattr(update_data, field) is not None for field in fields):
                    raise ValueError("At least one message field is required")
                result = await group_service.update_message(
                    db=db,
                    group_id=group_id,
                    message_id=message_id,
                    user_id=user_id,
                    body=update_data.body,
                    media_type=update_data.media_type,
                    media_urls=update_data.media_urls,
                    media_names=update_data.media_names,
                )
                frame = {
                    "type": "group_message_updated",
                    "group_id": group_id,
                    "data": result["data"]["message"],
                    "sender": result["data"]["sender"],
                }
            else:
                await group_service.delete_message(
                    db=db,
                    group_id=group_id,
                    message_id=message_id,
                    user_id=user_id,
                )
                frame = {
                    "type": "group_message_deleted",
                    "data": {
                        "group_id": group_id,
                        "message_id": message_id,
                        "sender_id": user_id,
                    },
                }
    except Exception as exc:
        await _send_json_safe(
            websocket,
            {
                "type": "error",
                "error": f"{message_type}.failed",
                "message": str(exc),
            },
            send_lock,
        )
        return

    published = await _publish_group_frame(
        redis=redis, member_ids=member_ids, payload=frame
    )
    if not published:
        await _send_json_safe(
            websocket,
            {
                "type": "error",
                "error": "group.message.delivery_failed",
                "message": "The change was saved; reload the group history to sync it",
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
        is_forbidden = isinstance(exc, ForbiddenException)
        await _send_json_safe(
            websocket,
            {
                "type": "error",
                "error": (
                    "group.access.denied" if is_forbidden else "group.message.failed"
                ),
                "message": (
                    "You are not an active member of this group"
                    if is_forbidden
                    else str(exc)
                ),
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

    await _publish_group_frame(
        redis=redis,
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
            result = await db.execute(
                select(GroupMember.user_id, User.username)
                .join(User, User.id == GroupMember.user_id)
                .where(
                    GroupMember.group_id == group_id,
                    GroupMember.is_active.is_(True),
                )
            )
            active_members = result.all()
    except Exception:
        logger.exception(
            "Failed to load group members for typing event in group %s", group_id
        )
        await _send_json_safe(
            websocket,
            {
                "type": "error",
                "error": "group.access.failed",
                "message": "Could not verify access to this group",
            },
            send_lock,
        )
        return

    usernames_by_member_id = {
        str(member_id): username for member_id, username in active_members
    }
    if user_id not in usernames_by_member_id:
        await _send_json_safe(
            websocket,
            {
                "type": "error",
                "error": "group.access.denied",
                "message": "You are not an active member of this group",
            },
            send_lock,
        )
        return

    frame = {
        "type": "group_typing",
        "data": {
            "group_id": group_id,
            "user_id": user_id,
            "username": usernames_by_member_id[user_id],
            "is_typing": is_typing,
        },
    }
    targets = [
        member_id for member_id in usernames_by_member_id if member_id != user_id
    ]
    await _publish_group_frame(redis=redis, member_ids=targets, payload=frame)
