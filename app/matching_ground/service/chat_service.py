from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import Conversation, Message
from app.models.user import User
from app.utils.exception import ForbiddenException, NotFoundException
from app.worker.event_system import (
    EventNames,
    MobileEvent,
    PushNotificationEvent,
    dispatch_event,
)


class ChatService:
    async def get_or_create_conversation(
        self, *, db: AsyncSession, user1_id: uuid.UUID, user2_id: uuid.UUID
    ) -> Conversation:
        if user1_id == user2_id:
            raise ForbiddenException("You can't chat with yourself")
        return await Conversation.get_or_create_between(db, user1_id, user2_id)

    async def send_message(
        self,
        *,
        db: AsyncSession,
        redis,
        sender: User,
        recipient_id: uuid.UUID,
        body: str,
    ) -> dict:
        recipient = await User.get_by_id(str(recipient_id), db)
        conversation = await self.get_or_create_conversation(
            db=db, user1_id=sender.id, user2_id=recipient.id
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

        # Stream-friendly receipt event (frontend can use this to update UI quickly)
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

        return {
            "conversation_id": str(conversation.id),
            "message": msg.to_dict(),
        }

    async def list_conversations(
        self,
        *,
        db: AsyncSession,
        user_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        offset = (page - 1) * page_size
        stmt = (
            select(Conversation)
            .where((Conversation.user_a_id == user_id) | (Conversation.user_b_id == user_id))
            .order_by(desc(Conversation.last_message_at))
            .offset(offset)
            .limit(page_size)
        )
        result = await db.execute(stmt)
        rows = list(result.scalars().all())
        return {
            "items": [c.to_dict() for c in rows],
            "page": page,
            "page_size": page_size,
            "total": len(rows),
        }

    async def list_messages(
        self,
        *,
        db: AsyncSession,
        conversation_id: uuid.UUID,
        current_user_id: uuid.UUID,
        page: int = 1,
        page_size: int = 30,
    ) -> dict:
        conv = await Conversation.get_by_id(str(conversation_id), db)
        if current_user_id not in {conv.user_a_id, conv.user_b_id}:
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
        items = [m.to_dict() for m in result.scalars().all()]
        return {"items": items, "page": page, "page_size": page_size, "total": len(items)}

    async def get_conversation(
        self, *, db: AsyncSession, conversation_id: uuid.UUID, current_user_id: uuid.UUID
    ) -> dict:
        conv = await Conversation.get_by_id(str(conversation_id), db)
        if current_user_id not in {conv.user_a_id, conv.user_b_id}:
            raise NotFoundException("Conversation not found")
        return conv.to_dict()


chat_service = ChatService()
