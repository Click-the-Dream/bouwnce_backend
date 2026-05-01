import uuid
from datetime import datetime, timezone, timedelta

from sqlalchemy import DateTime, ForeignKey, String, select, and_
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Self

from app.models.basemodel import BaseModel


class Match(BaseModel):
    __tablename__ = "matches"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    target_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    chat_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_reason: Mapped[str | None] = mapped_column(String(120))


    @classmethod
    async def find_pair(cls, session: AsyncSession, user_a: uuid.UUID, user_b: uuid.UUID) -> Self | None:
        result = await session.execute(
            select(cls).where(
                and_(
                    Match.user_id == user_a,
                    Match.target_user_id == user_b,
                )
            )
        )
        return result.scalar_one_or_none()

    @classmethod
    async def find_active_between_any_direction(
        cls,
        session: AsyncSession,
        user_a: uuid.UUID,
        user_b: uuid.UUID,
    ) -> Self | None:
        result = await session.execute(
            select(cls).where(
                cls.status == "active",
                (
                    ((cls.user_id == user_a) & (cls.target_user_id == user_b))
                    | ((cls.user_id == user_b) & (cls.target_user_id == user_a))
                ),
            )
        )
        return result.scalar_one_or_none()

    @classmethod
    async def create_accepted(cls, session: AsyncSession, user_a: uuid.UUID, user_b: uuid.UUID) -> Self:
        existing = await Match.find_active_between_any_direction(session, user_a, user_b)
        if existing is not None:
            return existing
        now = datetime.now(timezone.utc)
        row = cls(
            user_id=user_a,
            target_user_id=user_b,
            status="active",
            accepted_at=now,
            chat_expires_at=now + timedelta(days=3),
        )
        session.add(row)
        await session.flush()
        return row

    
    async def close(self, session: AsyncSession, reason: str):
        self.status = "closed"
        self.closed_reason = reason
        self.closed_at = datetime.now(timezone.utc)
        await session.flush()
        return self

    @classmethod
    async def list_for_user(cls, session: AsyncSession, user_id: uuid.UUID) -> list[Self]:
        result = await session.execute(
            select(cls)
            .where((cls.user_id == user_id) | (cls.target_user_id == user_id))
            .order_by(cls.created_at.desc())
        )
        return list(result.scalars().all())

    @classmethod
    async def get_for_participant(
        cls,
        session: AsyncSession,
        match_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Self | None:
        result = await session.execute(
            select(cls).where(
                cls.id == match_id,
                ((cls.user_id == user_id) | (cls.target_user_id == user_id)),
            )
        )
        return result.scalar_one_or_none()

