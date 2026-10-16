from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Self
from uuid import UUID as UUID_Type

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
    select,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.dialects.postgresql import insert as pg_insert
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

    user_a: Mapped[User] = relationship(foreign_keys=[user_a_id], lazy="noload")
    user_b: Mapped[User] = relationship(foreign_keys=[user_b_id], lazy="noload")

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
        """Single-query upsert: INSERT ... ON CONFLICT DO UPDATE RETURNING *.

        Reduces 3 roundtrips (SELECT + INSERT + REFRESH) to 1.
        """
        a_id, b_id = cls.normalize_user_pair(user1_id, user2_id)
        now = func.now()
        stmt = (
            pg_insert(cls)
            .values(user_a_id=a_id, user_b_id=b_id)
            .on_conflict_do_update(
                constraint="uix_conversation_users",
                set_={"last_message_at": now},
            )
            .returning(cls)
        )
        result = await db.execute(stmt)
        return result.scalar_one()


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
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    body: Mapped[str] = mapped_column(String, nullable=False)
    edited_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_edited: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Media support
    media_type: Mapped[str | None] = mapped_column(
        String, nullable=True
    )  # image|video|file
    media_urls: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    media_name: Mapped[str | None] = mapped_column(String, nullable=True)
    reply_to_message_id: Mapped[UUID_Type | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="SET NULL"),
        nullable=True,
    )
    deleted_for_everyone_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    conversation: Mapped[Conversation] = relationship(lazy="noload")

    __table_args__ = (
        # Speeds up `ORDER BY created_at DESC` per-conversation message pages.
        Index("ix_messages_conversation_created", "conversation_id", "created_at"),
        # Speeds up unread counts / mark-as-read on unread rows for a user.
        Index(
            "ix_messages_recipient_unread",
            "recipient_id",
            postgresql_where=text("read_at IS NULL"),
        ),
    )


class MessageDeletion(BaseModel):
    """Per-user deletion markers for direct messages."""

    __tablename__ = "message_deletions"

    message_id: Mapped[UUID_Type] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[UUID_Type] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "message_id", "user_id", name="uq_message_deletions_message_user"
        ),
        Index("ix_message_deletions_user_message", "user_id", "message_id"),
    )


class Group(BaseModel):
    """Group chat model for many-to-many conversations."""

    __tablename__ = "groups"

    id: Mapped[UUID_Type] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(String(500))
    created_by: Mapped[UUID_Type] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    creator: Mapped[User] = relationship(foreign_keys=[created_by], lazy="joined")
    members: Mapped[list[GroupMember]] = relationship(
        "GroupMember",
        back_populates="group",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    messages: Mapped[list[GroupMessage]] = relationship(
        "GroupMessage",
        back_populates="group",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_groups_name", "name"),
        Index("ix_groups_created_by", "created_by"),
    )

    @property
    def member_count(self) -> int:
        """Get current number of members in the group."""
        return len(self.members) if self.members else 0

    @property
    def member_list(self) -> list[UUID_Type]:
        """Get list of member user IDs."""
        return [member.user_id for member in self.members] if self.members else []


class GroupMember(BaseModel):
    """Many-to-many relationship between Users and Groups."""

    __tablename__ = "group_members"

    id: Mapped[UUID_Type] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    group_id: Mapped[UUID_Type] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[UUID_Type] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(
        String(20), default="member", nullable=False
    )  # owner, admin, member, moderator
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), nullable=False
    )
    invited_by: Mapped[UUID_Type | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    group: Mapped[Group] = relationship(
        foreign_keys=[group_id], back_populates="members"
    )
    user: Mapped[User] = relationship(foreign_keys=[user_id])
    inviter: Mapped[User] = relationship(foreign_keys=[invited_by])

    __table_args__ = (
        UniqueConstraint("group_id", "user_id", name="uix_group_member"),
        Index("ix_group_members_group_id", "group_id"),
        Index("ix_group_members_user_id", "user_id"),
        Index("ix_group_members_role", "role"),
    )


class GroupMessage(BaseModel):
    """Message model for group chats."""

    __tablename__ = "group_messages"

    id: Mapped[UUID_Type] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    group_id: Mapped[UUID_Type] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id", ondelete="CASCADE"), nullable=False
    )
    sender_id: Mapped[UUID_Type] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    body: Mapped[str] = mapped_column(String, nullable=False)

    # Timestamp and metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), nullable=False
    )
    edited_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_edited: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deleted_for_everyone_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Message features
    media_type: Mapped[str | None] = mapped_column(
        String, nullable=True
    )  # image|video|file|audio
    media_urls: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    media_names: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    reply_to_message_id: Mapped[UUID_Type | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("group_messages.id"), nullable=True
    )

    # Mentions/tags - stores mentioned user IDs
    mentioned_user_ids: Mapped[list[UUID_Type] | None] = mapped_column(
        JSONB, nullable=True
    )

    # Read receipts tracking (simplified - could be expanded to per-user tracking)
    read_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    group: Mapped[Group] = relationship(
        foreign_keys=[group_id], back_populates="messages"
    )
    sender: Mapped[User] = relationship(foreign_keys=[sender_id])
    reply_to: Mapped[GroupMessage] = relationship(foreign_keys=[reply_to_message_id])

    __table_args__ = (
        Index("ix_group_messages_group_id", "group_id"),
        Index("ix_group_messages_sender_id", "sender_id"),
        Index("ix_group_messages_created_at", "created_at"),
        Index("ix_group_messages_reply_to", "reply_to_message_id"),
    )


class GroupMessageDeletion(BaseModel):
    """Per-user deletion markers for group messages."""

    __tablename__ = "group_message_deletions"

    message_id: Mapped[UUID_Type] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("group_messages.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[UUID_Type] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "message_id", "user_id", name="uq_group_message_deletions_message_user"
        ),
        Index("ix_group_message_deletions_user_message", "user_id", "message_id"),
    )
