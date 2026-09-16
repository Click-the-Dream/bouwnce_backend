from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import desc, func, select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.matching_ground.model.notification import Notification
from app.models.chat import Conversation, Message
from app.models.user import User

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class ChatRepository:
    async def create_notification(self, db: AsyncSession, data: dict) -> Notification:
        return await Notification.create(data=data, db=db)

    async def get_user(self, db: AsyncSession, user_id: str) -> User | None:
        users = await User.get_chat_users_by_ids([str(user_id)], db)
        return users[0] if users else None

    async def get_users(self, db: AsyncSession, user_ids: list[str]) -> list[User]:
        return await User.get_chat_users_by_ids(user_ids, db)

    async def get_conversation(
        self, db: AsyncSession, conversation_id: str
    ) -> Conversation:
        return await Conversation.get_by_id(str(conversation_id), db)

    async def get_conversation_between(
        self, db: AsyncSession, user_a_id: str, user_b_id: str
    ) -> Conversation | None:
        return await Conversation.get_between(
            db, uuid.UUID(str(user_a_id)), uuid.UUID(str(user_b_id))
        )

    async def get_or_create_conversation(
        self, db: AsyncSession, user_a_id: str, user_b_id: str
    ) -> Conversation:
        return await Conversation.get_or_create_between(db, user_a_id, user_b_id)

    async def create_message(
        self,
        *,
        db: AsyncSession,
        conversation_id,
        sender_id,
        recipient_id,
        body: str,
        reply_to_message_id: str | None = None,
        media_type: str | None = None,
        media_urls: list[str] | None = None,
        media_name: str | None = None,
    ) -> Message:
        stmt = (
            pg_insert(Message)
            .values(
                conversation_id=conversation_id,
                sender_id=sender_id,
                recipient_id=recipient_id,
                body=body,
                reply_to_message_id=reply_to_message_id,
                media_type=media_type,
                media_urls=media_urls,
                media_name=media_name,
            )
            .returning(Message)
        )
        return (await db.execute(stmt)).scalar_one()

    async def get_message(self, db: AsyncSession, message_id: str) -> Message:
        return await Message.get_by_id(str(message_id), db)

    async def find_message(self, db: AsyncSession, message_id: str) -> Message | None:
        return (
            await db.execute(
                select(Message).where(Message.id == uuid.UUID(str(message_id)))
            )
        ).scalar_one_or_none()

    async def get_messages_by_ids(
        self, db: AsyncSession, message_ids: set[str]
    ) -> list[Message]:
        if not message_ids:
            return []
        return list(
            (
                await db.execute(
                    select(Message).where(Message.id.in_(list(message_ids)))
                )
            ).scalars()
        )

    async def list_conversations(
        self, db: AsyncSession, user_id: str, page: int, page_size: int
    ) -> tuple[list[Conversation], int]:
        participant_filter = (Conversation.user_a_id == user_id) | (
            Conversation.user_b_id == user_id
        )
        total = int(
            (
                await db.execute(
                    select(func.count())
                    .select_from(Conversation)
                    .where(participant_filter)
                )
            ).scalar()
            or 0
        )
        latest_message_at = (
            select(func.max(Message.created_at))
            .where(Message.conversation_id == Conversation.id)
            .correlate(Conversation)
            .scalar_subquery()
        )
        rows = list(
            (
                await db.execute(
                    select(Conversation)
                    .where(participant_filter)
                    .order_by(
                        latest_message_at.desc().nullslast(),
                        Conversation.created_at.desc(),
                        Conversation.id.desc(),
                    )
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            ).scalars()
        )
        return rows, total

    async def get_latest_messages(
        self, db: AsyncSession, conversation_ids: list
    ) -> dict[str, Message]:
        if not conversation_ids:
            return {}
        rows = list(
            (
                await db.execute(
                    select(Message)
                    .where(Message.conversation_id.in_(conversation_ids))
                    .order_by(Message.conversation_id, desc(Message.created_at))
                    .distinct(Message.conversation_id)
                )
            ).scalars()
        )
        return {str(message.conversation_id): message for message in rows}

    async def get_unread_counts(
        self, db: AsyncSession, conversation_ids: list, recipient_id: str
    ) -> dict[str, int]:
        if not conversation_ids:
            return {}
        rows = (
            await db.execute(
                select(Message.conversation_id, func.count().label("unread_count"))
                .where(
                    Message.conversation_id.in_(conversation_ids),
                    Message.recipient_id == recipient_id,
                    Message.read_at.is_(None),
                )
                .group_by(Message.conversation_id)
            )
        ).all()
        return {
            str(conversation_id): int(count or 0) for conversation_id, count in rows
        }

    async def list_messages(
        self, db: AsyncSession, conversation_id, page: int, page_size: int
    ) -> tuple[list[Message], int]:
        total = int(
            (
                await db.execute(
                    select(func.count())
                    .select_from(Message)
                    .where(Message.conversation_id == conversation_id)
                )
            ).scalar()
            or 0
        )
        rows = list(
            (
                await db.execute(
                    select(Message)
                    .where(Message.conversation_id == conversation_id)
                    .order_by(desc(Message.created_at))
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            ).scalars()
        )
        return rows, total

    async def get_partner_ids(self, db: AsyncSession, user_id: str) -> set[str]:
        rows = (
            await db.execute(
                select(Conversation.user_a_id, Conversation.user_b_id).where(
                    (Conversation.user_a_id == user_id)
                    | (Conversation.user_b_id == user_id)
                )
            )
        ).all()
        return {
            str(partner_id)
            for user_a_id, user_b_id in rows
            for partner_id in (user_a_id, user_b_id)
            if str(partner_id) != str(user_id)
        }

    async def mark_messages_read(
        self,
        *,
        db: AsyncSession,
        conversation_id,
        recipient_id: str,
        read_at: datetime,
    ) -> int:
        result = await db.execute(
            update(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.recipient_id == recipient_id,
                Message.read_at.is_(None),
            )
            .values(read_at=read_at)
            .returning(text("1"))
        )
        return len(result.all())


chat_repository = ChatRepository()
