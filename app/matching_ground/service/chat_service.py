from __future__ import annotations

import uuid
import json
from datetime import UTC, datetime

from fastapi import status
from sqlalchemy import desc, select
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
    async def get_or_create_conversation(
        self, *, db: AsyncSession, user1_id: uuid.UUID, user2_id: uuid.UUID
    ) -> Conversation:
        if user1_id == user2_id:
            raise ForbiddenException("You can't chat with yourself")
        return await Conversation.get_or_create_between(db, user1_id, user2_id)

    # -----------------------------
    # Core methods (domain-level)
    # -----------------------------
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

        if redis is not None:
            await redis.publish(
                f"chat:conversation:{conversation.id}",
                json.dumps({"type": "chat.message", "data": msg.to_dict()}),
            )

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

        return {
            "conversation_id": str(conversation.id),
            "message": msg.to_dict(),
        }

    # -----------------------------
    # API-friendly wrappers (standard response_builder)
    # -----------------------------
    async def send_message_api(
        self,
        *,
        db: AsyncSession,
        redis,
        current_user: User,
        recipient_id: str,
        body: str,
    ) -> dict:
        result = await self.send_message(
            db=db,
            redis=redis,
            sender=current_user,
            recipient_id=uuid.UUID(recipient_id),
            body=body,
        )
        await db.commit()
        return response_builder(
            status_code=status.HTTP_201_CREATED,
            status="success",
            message="Message sent",
            data=result,
        )

    async def list_conversations_api(
        self,
        *,
        db: AsyncSession,
        user_id: uuid.UUID,
        page: int,
        page_size: int,
    ) -> dict:
        data = await self.list_conversations(
            db=db, user_id=user_id, page=page, page_size=page_size
        )
        return response_builder(
            status_code=status.HTTP_200_OK,
            status="success",
            message="Conversations fetched successfully",
            data=data,
        )

    async def list_user_conversations_api(
        self,
        *,
        db: AsyncSession,
        current_user: User,
        user_id: str,
        page: int,
        page_size: int,
    ) -> dict:
        target_id = uuid.UUID(user_id)
        if target_id != current_user.id:
            raise ForbiddenException(message="Forbidden")
        return await self.list_conversations_api(
            db=db, user_id=target_id, page=page, page_size=page_size
        )

    async def get_conversation_api(
        self,
        *,
        db: AsyncSession,
        current_user_id: uuid.UUID,
        conversation_id: str,
    ) -> dict:
        data = await self.get_conversation(
            db=db,
            conversation_id=uuid.UUID(conversation_id),
            current_user_id=current_user_id,
        )
        return response_builder(
            status_code=status.HTTP_200_OK,
            status="success",
            message="Conversation fetched successfully",
            data=data,
        )

    async def get_or_create_conversation_with_user_api(
        self,
        *,
        db: AsyncSession,
        current_user_id: uuid.UUID,
        user_id: str,
    ) -> dict:
        conv = await self.get_or_create_conversation(
            db=db, user1_id=current_user_id, user2_id=uuid.UUID(user_id)
        )
        await db.commit()
        return response_builder(
            status_code=status.HTTP_200_OK,
            status="success",
            message="Conversation ready",
            data=conv.to_dict(),
        )

    async def list_messages_api(
        self,
        *,
        db: AsyncSession,
        current_user_id: uuid.UUID,
        conversation_id: str,
        page: int,
        page_size: int,
    ) -> dict:
        data = await self.list_messages(
            db=db,
            conversation_id=uuid.UUID(conversation_id),
            current_user_id=current_user_id,
            page=page,
            page_size=page_size,
        )
        return response_builder(
            status_code=status.HTTP_200_OK,
            status="success",
            message="Messages fetched successfully",
            data=data,
        )

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
