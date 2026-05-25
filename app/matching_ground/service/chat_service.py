from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

from fastapi import status
from sqlalchemy import desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import Conversation, Message
from app.models.user import User
from app.utils.exception import ForbiddenException, NotFoundException
from app.utils.responses import response_builder
from app.worker.event_system import (
    EventNames,
    MobileEvent,
    PushNotificationEvent,
    dispatch_event,
)


class ChatService:
    @staticmethod
    def _extract_profile_pic_url(user: User) -> str | None:
        value = getattr(user, "profile_pic", None)
        if not value:
            return None
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            url_val = value.get("url")
            if isinstance(url_val, str):
                return url_val
            if isinstance(url_val, dict):
                nested = url_val.get("url")
                return nested if isinstance(nested, str) else None
        return None

    @staticmethod
    def _serialize_profile_pic(user: User) -> dict | None:
        url = ChatService._extract_profile_pic_url(user)
        if not url:
            return None
        return {"url": url}

    @staticmethod
    def _serialize_user(user: User) -> dict:
        return {
            "id": str(user.id),
            "username": user.username,
            "full_name": user.full_name,
            "profile_pic": ChatService._serialize_profile_pic(user),
        }

    @staticmethod
    def _serialize_conversation(conv: Conversation, *, current_user_id: str) -> dict:
        """
        API-safe conversation dict including the other participant's identity.
        """
        base = {
            "id": str(conv.id),
            "user_a_id": str(conv.user_a_id),
            "user_b_id": str(conv.user_b_id),
            "last_message_at": (
                conv.last_message_at.isoformat()
                if getattr(conv, "last_message_at", None)
                else None
            ),
            "created_at": conv.created_at.isoformat() if conv.created_at else None,
            "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
        }

        current_id = str(current_user_id)
        other = conv.user_b if current_id == str(conv.user_a_id) else conv.user_a
        base["user"] = {
            "id": str(other.id),
            "username": other.username,
            "full_name": other.full_name,
            "profile_pic": ChatService._serialize_profile_pic(other),
        }
        return base

    @classmethod
    def _serialize_message(
        cls, msg: Message, *, sender: User | None = None, recipient: User | None = None
    ) -> dict:
        data = msg.to_dict()
        if sender is not None:
            data["sender"] = cls._serialize_user(sender)
        if recipient is not None:
            data["recipient"] = cls._serialize_user(recipient)
        return data

    @classmethod
    def _serialize_reply_message(
        cls, msg: Message, *, sender: User | None = None, recipient: User | None = None
    ) -> dict:
        # Minimal, non-recursive representation for replies.
        data = msg.to_dict()
        if sender is not None:
            data["sender"] = cls._serialize_user(sender)
        if recipient is not None:
            data["recipient"] = cls._serialize_user(recipient)
        data.pop("reply_to_message_id", None)
        data.pop("reply_to_message", None)
        return data

    async def get_or_create_conversation(
        self, *, db: AsyncSession, user1_id: str, user2_id: str
    ) -> Conversation:
        if str(user1_id) == str(user2_id):
            raise ForbiddenException("You can't chat with yourself")
        return await Conversation.get_or_create_between(db, user1_id, user2_id)

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
    ) -> dict:
        recipient = await User.get_by_id(str(recipient_id), db)
        conversation = await self.get_or_create_conversation(
            db=db, user1_id=str(sender.id), user2_id=str(recipient.id)
        )

        msg = Message(
            conversation_id=conversation.id,
            sender_id=sender.id,
            recipient_id=recipient.id,
            body=body.strip(),
            reply_to_message_id=reply_to_message_id,
        )
        db.add(msg)

        conversation.last_message_at = datetime.now(UTC)
        await db.flush()
        await db.refresh(msg)

        reply_obj: dict | bool = False
        if msg.reply_to_message_id:
            reply_row = (
                await db.execute(
                    select(Message).where(Message.id == msg.reply_to_message_id)
                )
            ).scalar_one_or_none()
            if reply_row is not None:
                reply_sender = await User.get_by_id(str(reply_row.sender_id), db)
                reply_recipient = await User.get_by_id(str(reply_row.recipient_id), db)
                reply_obj = self._serialize_reply_message(
                    reply_row, sender=reply_sender, recipient=reply_recipient
                )

        if redis is not None:
            msg_payload = self._serialize_message(
                msg, sender=sender, recipient=recipient
            )
            msg_payload["reply_to_message"] = reply_obj
            await redis.publish(
                f"chat:conversation:{conversation.id}",
                json.dumps({"type": "chat.message", "data": msg_payload}),
            )
            # User-level fanout (single inbox websocket can subscribe to this)
            payload = json.dumps({"type": "chat.message", "data": msg_payload})
            await redis.publish(f"chat:user:{sender.id}", payload)
            await redis.publish(f"chat:user:{recipient.id}", payload)

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
                    "conversation_id": str(conversation.id),
                    "message_id": str(msg.id),
                    "sender_id": str(sender.id),
                    "recipient_id": str(recipient.id),
                },
            ),
            db=db,
            redis=redis,
        )

        result = {
            "conversation_id": str(conversation.id),
            "message": {
                **self._serialize_message(msg, sender=sender, recipient=recipient),
                "reply_to_message": reply_obj,
            },
        }

        if commit:
            await db.commit()

        if as_response:
            return response_builder(
                status_code=status.HTTP_201_CREATED,
                status="success",
                message="Message sent",
                data=result,
            )

        return result

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
    ) -> dict:
        recipient = await User.get_by_id(str(recipient_id), db)
        conversation = await self.get_or_create_conversation(
            db=db, user1_id=str(sender.id), user2_id=str(recipient.id)
        )

        urls = [u for u in (media_urls or []) if u]
        # de-dupe while preserving order
        seen: set[str] = set()
        urls = [u for u in urls if not (u in seen or seen.add(u))]

        msg = Message(
            conversation_id=conversation.id,
            sender_id=sender.id,
            recipient_id=recipient.id,
            body=(body or "").strip(),
            media_type=media_type,
            media_urls=(urls or None),
            media_name=(file_name.strip() if isinstance(file_name, str) and file_name.strip() else None),
            reply_to_message_id=reply_to_message_id,
        )
        db.add(msg)

        conversation.last_message_at = datetime.now(UTC)
        await db.flush()
        await db.refresh(msg)

        reply_obj: dict | bool = False
        if msg.reply_to_message_id:
            reply_row = (
                await db.execute(
                    select(Message).where(Message.id == msg.reply_to_message_id)
                )
            ).scalar_one_or_none()
            if reply_row is not None:
                reply_sender = await User.get_by_id(str(reply_row.sender_id), db)
                reply_recipient = await User.get_by_id(str(reply_row.recipient_id), db)
                reply_obj = self._serialize_reply_message(
                    reply_row, sender=reply_sender, recipient=reply_recipient
                )

        if redis is not None:
            msg_payload = self._serialize_message(
                msg, sender=sender, recipient=recipient
            )
            msg_payload["reply_to_message"] = reply_obj
            payload = json.dumps({"type": "chat.message", "data": msg_payload})
            await redis.publish(f"chat:conversation:{conversation.id}", payload)
            await redis.publish(f"chat:user:{sender.id}", payload)
            await redis.publish(f"chat:user:{recipient.id}", payload)

        result = {
            "conversation_id": str(conversation.id),
            "message": {
                **self._serialize_message(msg, sender=sender, recipient=recipient),
                "reply_to_message": reply_obj,
            },
        }

        if commit:
            await db.commit()

        if as_response:
            return response_builder(
                status_code=status.HTTP_201_CREATED,
                status="success",
                message="Message sent",
                data=result,
            )

        return result

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
        if rows:
            conv_ids = [c.id for c in rows]
            last_stmt = (
                select(Message)
                .where(Message.conversation_id.in_(conv_ids))
                # Postgres DISTINCT ON via SQLAlchemy .distinct(col)
                .order_by(Message.conversation_id, desc(Message.created_at))
                .distinct(Message.conversation_id)
            )
            last_result = await db.execute(last_stmt)
            last_msgs = list(last_result.scalars().all())
            last_by_conversation_id = {str(m.conversation_id): m for m in last_msgs}

        data = {
            "items": [],
            "page": page,
            "page_size": page_size,
            "total": len(rows),
        }

        for conv in rows:
            conv_data = self._serialize_conversation(conv, current_user_id=user_id)
            last = last_by_conversation_id.get(str(conv.id))
            conv_data["last_message"] = last.to_dict() if last is not None else False
            data["items"].append(conv_data)

        if as_response:
            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Conversations fetched successfully",
                data=data,
            )
        return data

    async def get_conversation_partner_ids(
        self, *, db: AsyncSession, user_id: str
    ) -> set[str]:
        """
        Return ids of users that have a conversation with `user_id`.
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
            users_result = await db.execute(
                select(User).where(User.id.in_(list(user_ids)))
            )
            users_by_id = {str(u.id): u for u in users_result.scalars().all()}

        items: list[dict] = []
        for m in msgs:
            row = self._serialize_message(
                m,
                sender=users_by_id.get(str(m.sender_id)),
                recipient=users_by_id.get(str(m.recipient_id)),
            )
            if m.reply_to_message_id:
                reply = reply_by_id.get(str(m.reply_to_message_id))
                if reply is not None:
                    row["reply_to_message"] = self._serialize_reply_message(
                        reply,
                        sender=users_by_id.get(str(reply.sender_id)),
                        recipient=users_by_id.get(str(reply.recipient_id)),
                    )
                else:
                    row["reply_to_message"] = False
            else:
                row["reply_to_message"] = False
            items.append(row)
        data = {"items": items, "page": page, "page_size": page_size, "total": total}
        if as_response:
            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Messages fetched successfully",
                data=data,
            )
        return data

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
        data: dict = {
            "conversation": self._serialize_conversation(
                conv, current_user_id=current_user_id
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
        data: dict = {
            "conversation": self._serialize_conversation(
                conv, current_user_id=current_user_id
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

    async def mark_conversation_read(
        self,
        *,
        db: AsyncSession,
        redis=None,
        conversation_id: str,
        current_user_id: str,
        commit: bool = False,
        as_response: bool = False,
    ) -> dict:
        conv = await Conversation.get_by_id(str(conversation_id), db)
        current_id = str(current_user_id)
        if current_id not in {str(conv.user_a_id), str(conv.user_b_id)}:
            raise ForbiddenException("You cannot access this conversation")

        read_at = datetime.now(UTC)
        stmt = (
            update(Message)
            .where(
                Message.conversation_id == conv.id,
                Message.recipient_id == current_user_id,
                Message.read_at.is_(None),
            )
            .values(read_at=read_at)
        )
        result = await db.execute(stmt)
        updated = int(result.rowcount or 0)

        unread_stmt = (
            select(func.count())
            .select_from(Message)
            .where(
                Message.conversation_id == conv.id,
                Message.recipient_id == current_user_id,
                Message.read_at.is_(None),
            )
        )
        unread_remaining = int((await db.execute(unread_stmt)).scalar() or 0)

        data = {
            "conversation_id": str(conv.id),
            "reader_id": str(current_user_id),
            "read": unread_remaining == 0,
            "updated": updated,
        }

        if redis is not None and updated > 0:
            payload = json.dumps({"type": "chat.read.updated", "data": data})
            await redis.publish(f"chat:user:{conv.user_a_id}", payload)
            await redis.publish(f"chat:user:{conv.user_b_id}", payload)
        if commit:
            await db.commit()
        if as_response:
            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Conversation marked as read",
                data=data,
            )
        return data

    async def mark_conversation_read_up_to_message(
        self,
        *,
        db: AsyncSession,
        redis=None,
        current_user_id: str,
        conversation_id: str,
        message_id: str,
        commit: bool = False,
        as_response: bool = False,
    ) -> dict:
        conv = await Conversation.get_by_id(str(conversation_id), db)
        current_id = str(current_user_id)
        if current_id not in {str(conv.user_a_id), str(conv.user_b_id)}:
            raise ForbiddenException("You cannot access this conversation")

        target = await Message.get_by_id(str(message_id), db)
        if str(target.conversation_id) != str(conv.id):
            raise NotFoundException("Message not found")
        if str(target.recipient_id) != current_id:
            raise ForbiddenException("You can only mark received messages as read")

        read_at = datetime.now(UTC)
        stmt = (
            update(Message)
            .where(
                Message.conversation_id == conv.id,
                Message.recipient_id == current_id,
                Message.read_at.is_(None),
            )
            .values(read_at=read_at)
        )
        result = await db.execute(stmt)
        updated = int(result.rowcount or 0)

        unread_stmt = (
            select(func.count())
            .select_from(Message)
            .where(
                Message.conversation_id == conv.id,
                Message.recipient_id == current_id,
                Message.read_at.is_(None),
            )
        )
        unread_remaining = int((await db.execute(unread_stmt)).scalar() or 0)

        data = {
            "conversation_id": str(conv.id),
            "message_id": str(target.id),
            "read": unread_remaining == 0,
            "updated": updated,
        }

        if redis is not None and updated > 0:
            payload = json.dumps(
                {
                    "type": "chat.read.updated",
                    "data": {
                        **data,
                        "reader_id": current_id,
                    },
                }
            )
            await redis.publish(f"chat:user:{conv.user_a_id}", payload)
            await redis.publish(f"chat:user:{conv.user_b_id}", payload)

        if commit:
            await db.commit()

        if as_response:
            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Messages marked as read",
                data=data,
            )

        return data

    async def mark_conversation_read_with_user_up_to_message(
        self,
        *,
        db: AsyncSession,
        redis=None,
        current_user_id: str,
        recipient_id: str,
        message_id: str,
        commit: bool = False,
        as_response: bool = False,
    ) -> dict:
        current_id = str(current_user_id)
        other_id = str(recipient_id)
        if current_id == other_id:
            raise ForbiddenException("You can't mark messages with yourself")

        conv = await Conversation.get_between(
            db, uuid.UUID(current_id), uuid.UUID(other_id)
        )
        if conv is None:
            data = {
                "conversation_id": False,
                "message_id": str(message_id),
                "read": False,
                "updated": 0,
                "found": False,
            }
            if as_response:
                return response_builder(
                    status_code=status.HTTP_200_OK,
                    status="success",
                    message="No conversation found",
                    data=data,
                )
            return data

        if current_id not in {str(conv.user_a_id), str(conv.user_b_id)}:
            raise ForbiddenException("You cannot access this conversation")

        target = (
            await db.execute(
                select(Message).where(Message.id == uuid.UUID(str(message_id)))
            )
        ).scalar_one_or_none()
        if target is None or str(target.conversation_id) != str(conv.id):
            data = {
                "conversation_id": str(conv.id),
                "message_id": str(message_id),
                "read": False,
                "updated": 0,
                "found": True,
            }
            if as_response:
                return response_builder(
                    status_code=status.HTTP_200_OK,
                    status="success",
                    message="Message not found in conversation",
                    data=data,
                )
            return data

        if str(target.recipient_id) != current_id:
            raise ForbiddenException("You can only mark received messages as read")

        read_at = datetime.now(UTC)
        stmt = (
            update(Message)
            .where(
                Message.conversation_id == conv.id,
                Message.recipient_id == current_id,
                Message.read_at.is_(None),
            )
            .values(read_at=read_at)
        )
        result = await db.execute(stmt)
        updated = int(result.rowcount or 0)

        unread_stmt = (
            select(func.count())
            .select_from(Message)
            .where(
                Message.conversation_id == conv.id,
                Message.recipient_id == current_id,
                Message.read_at.is_(None),
            )
        )
        unread_remaining = int((await db.execute(unread_stmt)).scalar() or 0)

        data = {
            "conversation_id": str(conv.id),
            "message_id": str(target.id),
            "read": unread_remaining == 0,
            "updated": updated,
            "found": True,
        }

        if redis is not None and updated > 0:
            payload = json.dumps(
                {
                    "type": "chat.read.updated",
                    "data": {
                        "conversation_id": str(conv.id),
                        "message_id": str(target.id),
                        "updated": updated,
                        "read": unread_remaining == 0,
                        "reader_id": current_id,
                    },
                }
            )
            await redis.publish(f"chat:user:{conv.user_a_id}", payload)
            await redis.publish(f"chat:user:{conv.user_b_id}", payload)

        if commit:
            await db.commit()

        if as_response:
            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Messages marked as read",
                data=data,
            )

        return data


chat_service = ChatService()
