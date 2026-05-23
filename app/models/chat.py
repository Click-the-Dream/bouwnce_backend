from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Self
from uuid import UUID as UUID_Type

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func, select
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.basemodel import BaseModel

if TYPE_CHECKING:
    from app.models import User


class Conversation(BaseModel):
    __tablename__ = "conversations"

    user_a_id: Mapped[UUID_Type] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    user_b_id: Mapped[UUID_Type] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    last_message_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), nullable=False
    )

    user_a: Mapped["User"] = relationship(foreign_keys=[user_a_id], lazy="joined")
    user_b: Mapped["User"] = relationship(foreign_keys=[user_b_id], lazy="joined")

    __table_args__ = (
        UniqueConstraint("user_a_id", "user_b_id", name="uix_conversation_users"),
    )

    @staticmethod
    def normalize_user_pair(
        user1_id: UUID_Type, user2_id: UUID_Type
    ) -> tuple[UUID_Type, UUID_Type]:
        if str(user1_id) < str(user2_id):
            return user1_id, user2_id
        return user2_id, user1_id

    @classmethod
    async def get_between(
        cls, db: AsyncSession, user1_id: UUID_Type, user2_id: UUID_Type
    ) -> Self | None:
        a_id, b_id = cls.normalize_user_pair(user1_id, user2_id)
        result = await db.execute(
            select(cls).where(cls.user_a_id == a_id, cls.user_b_id == b_id)
        )
        return result.scalar_one_or_none()

    @classmethod
    async def get_or_create_between(
        cls, db: AsyncSession, user1_id: UUID_Type, user2_id: UUID_Type
    ) -> Self:
        existing = await cls.get_between(db, user1_id, user2_id)
        if existing is not None:
            return existing
        a_id, b_id = cls.normalize_user_pair(user1_id, user2_id)
        row = cls(user_a_id=a_id, user_b_id=b_id)
        db.add(row)
        await db.flush()
        await db.refresh(row)
        return row


class Message(BaseModel):
    __tablename__ = "messages"

    conversation_id: Mapped[UUID_Type] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sender_id: Mapped[UUID_Type] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    recipient_id: Mapped[UUID_Type] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    body: Mapped[str] = mapped_column(String, nullable=False)

    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Media support
    media_type: Mapped[str | None] = mapped_column(String, nullable=True)  # image|video|file
    media_urls: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    reply_to_message_id: Mapped[UUID_Type | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("messages.id", ondelete="SET NULL"), nullable=True
    )

    conversation: Mapped[Conversation] = relationship(lazy="joined")
