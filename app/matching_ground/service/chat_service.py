"""Chat service — send, list, get conversations and messages.

The heavy logic lives in:
  - chat_utils.py  (ChatSerializers) — serialization + batch loaders
  - chat_read.py   (ChatReadOps)     — mark_conversation_read variants

This file stays ~600 lines: send_message, send_media_message, list, get, partner_ids.
"""

from __future__ import annotations

from fastapi import status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import CHAT_EVENTS_STREAM_KEY_PREFIX, settings
from app.matching_ground.model.notification import Notification
from app.matching_ground.service.chat_read import ChatReadOps
from app.models.chat import Conversation, Message
from app.models.user import User
from app.utils.chat_utils import ChatSerializers
from app.utils.exception import ForbiddenException, NotFoundException
from app.utils.message_insert import insert_message
from app.utils.responses import response_builder
from app.worker.event_system import (
    EventNames,
    MobileEvent,
    PushNotificationEvent,
    dispatch_event,
)


class ChatService(ChatSerializers, ChatReadOps):
    """Chat business logic — inherits serialization + read-status mixins."""

    async def get_or_create_conversation(
        self, *, db: AsyncSession, user1_id: str, user2_id: str
    ) -> Conversation:
        if str(user1_id) == str(user2_id):
            raise ForbiddenException("You can't chat with yourself")
        return await Conversation.get_or_create_between(db, user1_id, user2_id)

    # ------------------------------------------------------------------
    # send_message
    # ------------------------------------------------------------------
    async def send_message(
        self,
        *,
        db: AsyncSession,
        redis,
        sender: User,
        recipient_id: str,
        body: str,
        reply_to_message_id: str | None = None,
        commit: bool = False,
        as_response: bool = False,
        persist_notification: bool = True,
        notify_side_effects: bool = True,
        publish_redis_fanout: bool = True,
    ) -> dict:
        recipient_users = await User.get_chat_users_by_ids([str(recipient_id)], db)
        if not recipient_users:
            raise NotFoundException("Recipient not found")
        recipient = recipient_users[0]
        recipient_is_bouwnce = (
            settings.BOUWNCE_SYSTEM_EMAIL
            and recipient.email == settings.BOUWNCE_SYSTEM_EMAIL
        ) or (
            settings.BOUWNCE_SYSTEM_USERNAME
            and recipient.username == settings.BOUWNCE_SYSTEM_USERNAME
        )
        sender_is_bouwnce = (
            settings.BOUWNCE_SYSTEM_EMAIL
            and sender.email == settings.BOUWNCE_SYSTEM_EMAIL
        ) or (
            settings.BOUWNCE_SYSTEM_USERNAME
            and sender.username == settings.BOUWNCE_SYSTEM_USERNAME
        )
        if recipient_is_bouwnce and not sender_is_bouwnce:
            raise ForbiddenException("You cannot reply to Bouwnce inbox")
        conversation = await self.get_or_create_conversation(
            db=db, user1_id=str(sender.id), user2_id=str(recipient.id)
        )

        msg = await insert_message(
            db=db,
            conversation_id=conversation.id,
            sender_id=sender.id,
            recipient_id=recipient.id,
            body=body.strip(),
            reply_to_message_id=reply_to_message_id,
        )

        if persist_notification:
            await Notification.create(
                data={
                    "user_id": recipient.id,
                    "title": sender.full_name or sender.username or "New message",
                    "body": body[:120],
                    "event_type": "chat_message",
                    "payload": {
                        "route": "chat.conversation",
                        "conversation_id": str(conversation.id),
                        "message_id": str(msg.id),
                        "sender": self._serialize_user(sender),
                    },
                },
                db=db,
            )

        reply_obj: dict | bool = False
        if msg.reply_to_message_id:
            reply_row = (
                await db.execute(
                    select(Message).where(Message.id == msg.reply_to_message_id)
                )
            ).scalar_one_or_none()
            if reply_row is not None:
                reply_user_ids = [
                    str(reply_row.sender_id),
                    str(reply_row.recipient_id),
                ]
                reply_users = await User.get_chat_users_by_ids(reply_user_ids, db)
                reply_users_map = {str(u.id): u for u in reply_users}
                reply_payload = reply_row.to_dict()
                reply_payload["sender"] = self._serialize_user(
                    reply_users_map[str(reply_row.sender_id)]
                )
                reply_payload["recipient"] = self._serialize_user(
                    reply_users_map[str(reply_row.recipient_id)]
                )
                reply_payload.pop("reply_to_message_id", None)
                reply_payload.pop("reply_to_message", None)
                reply_obj = reply_payload

        if commit:
            await db.commit()

        if redis is not None and publish_redis_fanout:
            chat_message_event = self._build_chat_message_event(
                msg=msg,
                sender=sender,
                recipient=recipient,
                reply_obj=reply_obj,
            )
            payload = chat_message_event.model_dump_json()
            async with redis.pipeline() as pipe:
                pipe.publish(f"chat:conversation:{conversation.id}", payload)
                pipe.publish(f"chat:user:{sender.id}", payload)
                pipe.publish(f"chat:user:{recipient.id}", payload)
                pipe.xadd(
                    f"{CHAT_EVENTS_STREAM_KEY_PREFIX}{recipient.id}",
                    {"type": "chat.message", "data": payload},
                    maxlen=5000,
                    approximate=True,
                )
                await pipe.execute()

        if notify_side_effects:
            await dispatch_event(
                EventNames.PUSH_NOTIFICATION,
                PushNotificationEvent(
                    user_id=str(recipient.id),
                    title=(sender.full_name or sender.username or "New message"),
                    body=body[:80],
                    data={
                        "type": "chat.message.created",
                        "conversation_id": str(conversation.id),
                        "message_id": str(msg.id),
                    },
                ),
                db=db,
                redis=redis,
            )

            await dispatch_event(
                EventNames.MOBILE_EVENT,
                MobileEvent(
                    event_name="chat.message.created",
                    payload={
                        "user_id": str(recipient.id),
                        "conversation_id": str(conversation.id),
                        "message_id": str(msg.id),
                        "sender_id": str(sender.id),
                        "recipient_id": str(recipient.id),
                    },
                ),
                db=db,
                redis=redis,
            )

        message_data = self._build_chat_message_data(
            msg=msg, sender=sender, recipient=recipient, reply_obj=reply_obj
        )
        result = {
            "conversation_id": str(conversation.id),
            "message": message_data,
        }

        if as_response:
            return response_builder(
                status_code=status.HTTP_201_CREATED,
                status="success",
                message="Message sent",
                data={
                    "conversation_id": str(conversation.id),
                    "message": message_data.model_dump(mode="json"),
                },
            )

        return result

    # ------------------------------------------------------------------
    # send_media_message
    # ------------------------------------------------------------------
    async def send_media_message(
        self,
        *,
        db: AsyncSession,
        redis,
        sender: User,
        recipient_id: str,
        body: str | None = None,
        media_urls: list[str],
        media_type: str,
        file_name: str | None = None,
        reply_to_message_id: str | None = None,
        commit: bool = False,
        as_response: bool = False,
        persist_notification: bool = True,
        notify_side_effects: bool = True,
        publish_redis_fanout: bool = True,
    ) -> dict:
        recipient_users = await User.get_chat_users_by_ids([str(recipient_id)], db)
        if not recipient_users:
            raise NotFoundException("Recipient not found")
        recipient = recipient_users[0]
        recipient_is_bouwnce = (
            settings.BOUWNCE_SYSTEM_EMAIL
            and recipient.email == settings.BOUWNCE_SYSTEM_EMAIL
        ) or (
            settings.BOUWNCE_SYSTEM_USERNAME
            and recipient.username == settings.BOUWNCE_SYSTEM_USERNAME
        )
        sender_is_bouwnce = (
            settings.BOUWNCE_SYSTEM_EMAIL
            and sender.email == settings.BOUWNCE_SYSTEM_EMAIL
        ) or (
            settings.BOUWNCE_SYSTEM_USERNAME
            and sender.username == settings.BOUWNCE_SYSTEM_USERNAME
        )
        if recipient_is_bouwnce and not sender_is_bouwnce:
            raise ForbiddenException("You cannot reply to Bouwnce inbox")
        conversation = await self.get_or_create_conversation(
            db=db, user1_id=str(sender.id), user2_id=str(recipient.id)
        )

        urls = [u for u in (media_urls or []) if u]
        seen: set[str] = set()
        urls = [u for u in urls if not (u in seen or seen.add(u))]

        msg = await insert_message(
            db=db,
            conversation_id=conversation.id,
            sender_id=sender.id,
            recipient_id=recipient.id,
            body=(body or "").strip(),
            media_type=media_type,
            media_urls=urls or None,
            media_name=(
                file_name.strip()
                if isinstance(file_name, str) and file_name.strip()
                else None
            ),
            reply_to_message_id=reply_to_message_id,
        )

        if persist_notification:
            await Notification.create(
                data={
                    "user_id": recipient.id,
                    "title": sender.full_name or sender.username or "New message",
                    "body": (msg.body or "")[:120],
                    "event_type": "chat_message",
                    "payload": {
                        "route": "chat.conversation",
                        "conversation_id": str(conversation.id),
                        "message_id": str(msg.id),
                        "sender": self._serialize_user(sender),
                        "media_type": media_type,
                        "media_urls": urls,
                        "media_name": msg.media_name,
                    },
                },
                db=db,
            )

        reply_obj: dict | bool = False
        if msg.reply_to_message_id:
            reply_row = (
                await db.execute(
                    select(Message).where(Message.id == msg.reply_to_message_id)
                )
            ).scalar_one_or_none()
            if reply_row is not None:
                reply_user_ids = [
                    str(reply_row.sender_id),
                    str(reply_row.recipient_id),
                ]
                reply_users = await User.get_chat_users_by_ids(reply_user_ids, db)
                reply_users_map = {str(u.id): u for u in reply_users}
                reply_payload = reply_row.to_dict()
                reply_payload["sender"] = self._serialize_user(
                    reply_users_map[str(reply_row.sender_id)]
                )
                reply_payload["recipient"] = self._serialize_user(
                    reply_users_map[str(reply_row.recipient_id)]
                )
                reply_payload.pop("reply_to_message_id", None)
                reply_payload.pop("reply_to_message", None)
                reply_obj = reply_payload

        if commit:
            await db.commit()

        if redis is not None and publish_redis_fanout:
            chat_message_event = self._build_chat_message_event(
                msg=msg,
                sender=sender,
                recipient=recipient,
                reply_obj=reply_obj,
            )
            payload = chat_message_event.model_dump_json()
            async with redis.pipeline() as pipe:
                pipe.publish(f"chat:conversation:{conversation.id}", payload)
                pipe.publish(f"chat:user:{sender.id}", payload)
                pipe.publish(f"chat:user:{recipient.id}", payload)
                pipe.xadd(
                    f"{CHAT_EVENTS_STREAM_KEY_PREFIX}{recipient.id}",
                    {"type": "chat.message", "data": payload},
                    maxlen=5000,
                    approximate=True,
                )
                await pipe.execute()

        if notify_side_effects:
            await dispatch_event(
                EventNames.MOBILE_EVENT,
                MobileEvent(
                    event_name="chat.message.created",
                    payload={
                        "user_id": str(recipient.id),
                        "conversation_id": str(conversation.id),
                        "message_id": str(msg.id),
                        "sender_id": str(sender.id),
                        "recipient_id": str(recipient.id),
                        "media_type": media_type,
                        "media_urls": urls,
                        "media_name": msg.media_name,
                    },
                ),
                db=db,
                redis=redis,
            )

        message_data = self._build_chat_message_data(
            msg=msg, sender=sender, recipient=recipient, reply_obj=reply_obj
        )
        result = {
            "conversation_id": str(conversation.id),
            "message": message_data,
        }

        if as_response:
            return response_builder(
                status_code=status.HTTP_201_CREATED,
                status="success",
                message="Message sent",
                data={
                    "conversation_id": str(conversation.id),
                    "message": message_data.model_dump(mode="json"),
                },
            )

        return result

    # ------------------------------------------------------------------
    # list_conversations
    # ------------------------------------------------------------------
    async def list_conversations(
        self,
        *,
        db: AsyncSession,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        as_response: bool = False,
    ) -> dict:
        offset = (page - 1) * page_size
        stmt = (
            select(Conversation)
            .where(
                (Conversation.user_a_id == user_id)
                | (Conversation.user_b_id == user_id)
            )
            .order_by(desc(Conversation.last_message_at))
            .offset(offset)
            .limit(page_size)
        )
        result = await db.execute(stmt)
        rows = list(result.scalars().all())

        last_by_conversation_id: dict[str, Message] = {}
        unread_by_conversation_id: dict[str, int] = {}
        if rows:
            conv_ids = [c.id for c in rows]
            last_stmt = (
                select(Message)
                .where(Message.conversation_id.in_(conv_ids))
                .order_by(Message.conversation_id, desc(Message.created_at))
                .distinct(Message.conversation_id)
            )
            last_result = await db.execute(last_stmt)
            last_msgs = list(last_result.scalars().all())
            last_by_conversation_id = {str(m.conversation_id): m for m in last_msgs}

            unread_stmt = (
                select(
                    Message.conversation_id,
                    func.count().label("unread_count"),
                )
                .where(
                    Message.conversation_id.in_(conv_ids),
                    Message.recipient_id == user_id,
                    Message.read_at.is_(None),
                )
                .group_by(Message.conversation_id)
            )
            unread_result = await db.execute(unread_stmt)
            unread_by_conversation_id = {
                str(conv_id): int(count or 0) for conv_id, count in unread_result.all()
            }

        users_by_id = await self._load_users_for_conversations(db, rows)

        data = {
            "items": [],
            "page": page,
            "page_size": page_size,
            "total": len(rows),
        }

        for conv in rows:
            conv_data = self._serialize_conversation(
                conv, current_user_id=user_id, users_by_id=users_by_id
            )
            last = last_by_conversation_id.get(str(conv.id))
            conv_data["last_message"] = last.to_dict() if last is not None else False
            conv_data["unread_count"] = unread_by_conversation_id.get(str(conv.id), 0)
            data["items"].append(conv_data)

        if as_response:
            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Conversations fetched successfully",
                data=data,
            )
        return data

    # ------------------------------------------------------------------
    # get_conversation_partner_ids
    # ------------------------------------------------------------------
    async def get_conversation_partner_ids(
        self, *, db: AsyncSession, user_id: str
    ) -> set[str]:
        """
        Return ids of users that have a conversation with ``user_id``.
        Used for presence fanout (online/offline).
        """
        stmt = select(Conversation.user_a_id, Conversation.user_b_id).where(
            (Conversation.user_a_id == user_id) | (Conversation.user_b_id == user_id)
        )
        result = await db.execute(stmt)
        partner_ids: set[str] = set()
        for a_id, b_id in result.all():
            a = str(a_id)
            b = str(b_id)
            if a != str(user_id):
                partner_ids.add(a)
            if b != str(user_id):
                partner_ids.add(b)
        return partner_ids

    # ------------------------------------------------------------------
    # list_messages
    # ------------------------------------------------------------------
    async def list_messages(
        self,
        *,
        db: AsyncSession,
        conversation_id: str,
        current_user_id: str,
        page: int = 1,
        page_size: int = 30,
        as_response: bool = False,
    ) -> dict:
        conv = await Conversation.get_by_id(str(conversation_id), db)
        current_id = str(current_user_id)
        if current_id not in {str(conv.user_a_id), str(conv.user_b_id)}:
            raise ForbiddenException("You cannot access this conversation")

        offset = (page - 1) * page_size
        total_stmt = (
            select(func.count())
            .select_from(Message)
            .where(Message.conversation_id == conv.id)
        )
        total = int((await db.execute(total_stmt)).scalar() or 0)

        stmt = (
            select(Message)
            .where(Message.conversation_id == conv.id)
            .order_by(desc(Message.created_at))
            .offset(offset)
            .limit(page_size)
        )
        result = await db.execute(stmt)
        msgs = list(result.scalars().all())

        reply_ids: set[str] = set()
        user_ids: set[str] = set()
        for m in msgs:
            user_ids.add(str(m.sender_id))
            user_ids.add(str(m.recipient_id))
            if m.reply_to_message_id:
                reply_ids.add(str(m.reply_to_message_id))

        reply_by_id: dict[str, Message] = {}
        if reply_ids:
            reply_result = await db.execute(
                select(Message).where(Message.id.in_(list(reply_ids)))
            )
            reply_rows = list(reply_result.scalars().all())
            reply_by_id = {str(r.id): r for r in reply_rows}
            for r in reply_rows:
                user_ids.add(str(r.sender_id))
                user_ids.add(str(r.recipient_id))

        users_by_id: dict[str, User] = {}
        if user_ids:
            users = await User.get_chat_users_by_ids(list(user_ids), db)
            users_by_id = {str(u.id): u for u in users}

        items: list[dict] = []
        for m in msgs:
            row = self._build_chat_message_data(
                msg=m,
                sender=users_by_id.get(str(m.sender_id)),
                recipient=users_by_id.get(str(m.recipient_id)),
                reply_obj=False,
            )
            if m.reply_to_message_id:
                reply = reply_by_id.get(str(m.reply_to_message_id))
                if reply is not None:
                    reply = self._build_chat_message_data(
                        msg=reply,
                        sender=users_by_id.get(str(reply.sender_id)),
                        recipient=users_by_id.get(str(reply.recipient_id)),
                        reply_obj=False,
                    )
                else:
                    reply = False
                row = row.model_copy(update={"reply_to_message": reply})
            items.append(row.model_dump(mode="json"))
        data = {"items": items, "page": page, "page_size": page_size, "total": total}
        if as_response:
            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Messages fetched successfully",
                data=data,
            )
        return data

    # ------------------------------------------------------------------
    # get_conversation
    # ------------------------------------------------------------------
    async def get_conversation(
        self,
        *,
        db: AsyncSession,
        conversation_id: str,
        current_user_id: str,
        include_messages: bool = True,
        messages_page: int = 1,
        messages_page_size: int = 30,
        as_response: bool = False,
    ) -> dict:
        conv = await Conversation.get_by_id(str(conversation_id), db)
        current_id = str(current_user_id)
        if current_id not in {str(conv.user_a_id), str(conv.user_b_id)}:
            raise NotFoundException("Conversation not found")
        users_by_id = await self._load_two_conversation_users(db, conv)
        data: dict = {
            "conversation": self._serialize_conversation(
                conv, current_user_id=current_user_id, users_by_id=users_by_id
            )
        }
        if include_messages:
            data["messages"] = await self.list_messages(
                db=db,
                conversation_id=str(conversation_id),
                current_user_id=current_user_id,
                page=messages_page,
                page_size=messages_page_size,
                as_response=False,
            )
        if as_response:
            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Conversation fetched successfully",
                data=data,
            )
        return data

    # ------------------------------------------------------------------
    # get_or_create_conversation_with_user
    # ------------------------------------------------------------------
    async def get_or_create_conversation_with_user(
        self,
        *,
        db: AsyncSession,
        current_user_id: str,
        user_id: str,
        include_messages: bool = True,
        messages_page: int = 1,
        messages_page_size: int = 30,
        commit: bool = False,
        as_response: bool = False,
    ) -> dict:
        conv = await self.get_or_create_conversation(
            db=db, user1_id=str(current_user_id), user2_id=str(user_id)
        )
        users_by_id = await self._load_two_conversation_users(db, conv)
        data: dict = {
            "conversation": self._serialize_conversation(
                conv, current_user_id=current_user_id, users_by_id=users_by_id
            )
        }
        if include_messages:
            data["messages"] = await self.list_messages(
                db=db,
                conversation_id=str(conv.id),
                current_user_id=current_user_id,
                page=messages_page,
                page_size=messages_page_size,
                as_response=False,
            )
        if commit:
            await db.commit()
        if as_response:
            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Conversation ready",
                data=data,
            )
        return data


chat_service = ChatService()
