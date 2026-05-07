from __future__ import annotations

import json
from datetime import UTC, datetime

from fastapi import status
from sqlalchemy import desc, select, update
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
    def _serialize_user(user: User) -> dict:
        return {
            "id": str(user.id),
            "username": user.username,
            "full_name": user.full_name,
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
            "last_message_at": conv.last_message_at.isoformat()
            if getattr(conv, "last_message_at", None)
            else None,
            "created_at": conv.created_at.isoformat() if conv.created_at else None,
            "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
        }

        current_id = str(current_user_id)
        other = conv.user_b if current_id == str(conv.user_a_id) else conv.user_a
        base["user"] = {
            "id": str(other.id),
            "username": other.username,
            "full_name": other.full_name,
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

    # -----------------------------
    # Core methods (domain-level)
    # -----------------------------
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
        )
        db.add(msg)

        conversation.last_message_at = datetime.now(UTC)
        await db.flush()
        await db.refresh(msg)

        if redis is not None:
            msg_payload = self._serialize_message(msg, sender=sender, recipient=recipient)
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
            "message": self._serialize_message(msg, sender=sender, recipient=recipient),
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
                (Conversation.user_a_id == user_id) | (Conversation.user_b_id == user_id)
            )
            .order_by(desc(Conversation.last_message_at))
            .offset(offset)
            .limit(page_size)
        )
        result = await db.execute(stmt)
        rows = list(result.scalars().all())
        data = {
            "items": [self._serialize_conversation(c, current_user_id=user_id) for c in rows],
            "page": page,
            "page_size": page_size,
            "total": len(rows),
        }
        if as_response:
            return response_builder(
                status_code=status.HTTP_200_OK,
                status="success",
                message="Conversations fetched successfully",
                data=data,
            )
        return data

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
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(desc(Message.created_at))
            .offset(offset)
            .limit(page_size)
        )
        result = await db.execute(stmt)
        msgs = list(result.scalars().all())

        user_ids: set[str] = set()
        for m in msgs:
            user_ids.add(str(m.sender_id))
            user_ids.add(str(m.recipient_id))

        users_by_id: dict[str, User] = {}
        if user_ids:
            users_result = await db.execute(select(User).where(User.id.in_(list(user_ids))))
            users_by_id = {str(u.id): u for u in users_result.scalars().all()}

        items = [
            self._serialize_message(
                m,
                sender=users_by_id.get(str(m.sender_id)),
                recipient=users_by_id.get(str(m.recipient_id)),
            )
            for m in msgs
        ]
        data = {"items": items, "page": page, "page_size": page_size, "total": len(items)}
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
        as_response: bool = False,
    ) -> dict:
        conv = await Conversation.get_by_id(str(conversation_id), db)
        current_id = str(current_user_id)
        if current_id not in {str(conv.user_a_id), str(conv.user_b_id)}:
            raise NotFoundException("Conversation not found")
        data: dict = {
            "conversation": self._serialize_conversation(conv, current_user_id=current_user_id)
        }
        if include_messages:
            data["messages"] = await self.list_messages(
                db=db,
                conversation_id=str(conversation_id),
                current_user_id=current_user_id,
                page=1,
                page_size=30,
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
        commit: bool = False,
        as_response: bool = False,
    ) -> dict:
        conv = await self.get_or_create_conversation(
            db=db, user1_id=str(current_user_id), user2_id=str(user_id)
        )
        data: dict = {
            "conversation": self._serialize_conversation(conv, current_user_id=current_user_id)
        }
        if include_messages:
            data["messages"] = await self.list_messages(
                db=db,
                conversation_id=str(conv.id),
                current_user_id=current_user_id,
                page=1,
                page_size=30,
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
        conversation_id: str,
        current_user_id: str,
        commit: bool = False,
        as_response: bool = False,
    ) -> dict:
        conv = await Conversation.get_by_id(str(conversation_id), db)
        current_id = str(current_user_id)
        if current_id not in {str(conv.user_a_id), str(conv.user_b_id)}:
            raise ForbiddenException("You cannot access this conversation")

        stmt = (
            update(Message)
            .where(
                Message.conversation_id == conv.id,
                Message.recipient_id == current_user_id,
                Message.read_at.is_(None),
            )
            .values(read_at=datetime.now(UTC))
        )
        result = await db.execute(stmt)
        updated = int(result.rowcount or 0)
        data = {"conversation_id": str(conv.id), "updated": updated}
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


chat_service = ChatService()
