"""Chat read-status mixin — mark_conversation_read and variants.

Extracted from chat_service.py to keep file sizes manageable.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.matching_ground.schema.chat import (
    ChatReadUpdatedData,
    ChatReadUpdatedEvent,
)
from app.models.chat import Conversation, Message
from app.utils.exception import ForbiddenException, NotFoundException
from app.utils.responses import response_builder


class ChatReadOps:
    """Conversation read-status operations."""

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
            .returning(text("1"))
        )
        result = await db.execute(stmt)
        updated = len(result.all())

        data = {
            "conversation_id": str(conv.id),
            "reader_id": str(current_user_id),
            "read": True,
            "updated": updated,
        }

        if redis is not None and updated > 0:
            payload = ChatReadUpdatedEvent(
                data=ChatReadUpdatedData(
                    conversation_id=str(conv.id),
                    reader_id=current_user_id,
                    read=True,
                    updated=updated,
                )
            ).model_dump_json()
            async with redis.pipeline() as pipe:
                pipe.publish(f"chat:user:{conv.user_a_id}", payload)
                pipe.publish(f"chat:user:{conv.user_b_id}", payload)
                await pipe.execute()
        if commit:
            await db.commit()
        if as_response:
            return response_builder(
                status_code=200,
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
            .returning(text("1"))
        )
        result = await db.execute(stmt)
        updated = len(result.all())

        data = {
            "conversation_id": str(conv.id),
            "message_id": str(target.id),
            "read": True,
            "updated": updated,
        }

        if redis is not None and updated > 0:
            payload = ChatReadUpdatedEvent(
                data=ChatReadUpdatedData(
                    conversation_id=str(conv.id),
                    message_id=str(target.id),
                    reader_id=current_id,
                    read=True,
                    updated=updated,
                )
            ).model_dump_json()
            async with redis.pipeline() as pipe:
                pipe.publish(f"chat:user:{conv.user_a_id}", payload)
                pipe.publish(f"chat:user:{conv.user_b_id}", payload)
                await pipe.execute()

        if commit:
            await db.commit()

        if as_response:
            return response_builder(
                status_code=200,
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
            }
            if as_response:
                return response_builder(
                    status_code=200,
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
            }
            if as_response:
                return response_builder(
                    status_code=200,
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
            .returning(text("1"))
        )
        result = await db.execute(stmt)
        updated = len(result.all())

        data = {
            "conversation_id": str(conv.id),
            "message_id": str(target.id),
            "read": True,
            "updated": updated,
        }

        if redis is not None and updated > 0:
            payload = ChatReadUpdatedEvent(
                data=ChatReadUpdatedData(
                    conversation_id=str(conv.id),
                    message_id=str(target.id),
                    reader_id=current_id,
                    read=True,
                    updated=updated,
                )
            ).model_dump_json()
            async with redis.pipeline() as pipe:
                pipe.publish(f"chat:user:{conv.user_a_id}", payload)
                pipe.publish(f"chat:user:{conv.user_b_id}", payload)
                await pipe.execute()

        if commit:
            await db.commit()

        if as_response:
            return response_builder(
                status_code=200,
                status="success",
                message="Messages marked as read",
                data=data,
            )

        return data
