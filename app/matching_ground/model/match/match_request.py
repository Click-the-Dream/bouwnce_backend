from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Self

from sqlalchemy import DateTime, ForeignKey, String, and_, select
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship, selectinload

from app.models.basemodel import BaseModel

if TYPE_CHECKING:
    from app.models.user import User


class MatchRequest(BaseModel):
    __tablename__ = "match_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    requester_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    target_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    note: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    requester: Mapped[User] = relationship("User", foreign_keys=[requester_id])
    target_user: Mapped[User] = relationship("User", foreign_keys=[target_user_id])

    @classmethod
    async def create_pending(
        cls,
        session: AsyncSession,
        requester_id: uuid.UUID,
        target_user_id: uuid.UUID,
        note: str | None,
        ttl_days: int = 7,
    ) -> Self:
        now = datetime.now(UTC)
        row = MatchRequest(
            requester_id=requester_id,
            target_user_id=target_user_id,
            note=note,
            status="pending",
            expires_at=now + timedelta(days=ttl_days),
        )
        session.add(row)
        await session.flush()
        return row

    @classmethod
    async def find_open_for_pair(
        cls,
        session: AsyncSession,
        requester_id: uuid.UUID,
        target_user_id: uuid.UUID,
    ) -> Self | None:
        result = await session.execute(
            select(cls).where(
                and_(
                    cls.requester_id == requester_id,
                    cls.target_user_id == target_user_id,
                    cls.status == "pending",
                )
            )
        )
        return result.scalar_one_or_none()

    async def set_status(self, session: AsyncSession, status: str) -> Self:
        self.status = status
        self.responded_at = datetime.now(UTC)
        await session.flush()
        return self

    @classmethod
    async def list_expired_pending(
        cls, session: AsyncSession, now: datetime | None = None
    ) -> list[Self]:
        now = now or datetime.now(UTC)
        result = await session.execute(
            select(cls).where(
                cls.status == "pending",
                cls.expires_at.is_not(None),
                cls.expires_at <= now,
            )
        )
        return list(result.scalars().all())

    @classmethod
    async def list_for_user(
        cls, session: AsyncSession, user_id: uuid.UUID, page: int, page_size: int
    ) -> list[Self]:
        result = await session.execute(
            select(cls)
            .where(cls.target_user_id == user_id)
            .options(selectinload(cls.requester), selectinload(cls.target_user))
            .offset((page - 1) * page_size)
            .limit(page_size)
            .order_by(cls.created_at.desc())
        )
        return list(result.scalars().all())

    @classmethod
    async def list_sent_by_user(
        cls, session: AsyncSession, user_id: uuid.UUID, page: int, page_size: int
    ) -> list[Self]:
        result = await session.execute(
            select(cls)
            .where(cls.requester_id == user_id)
            .options(selectinload(cls.requester), selectinload(cls.target_user))
            .offset((page - 1) * page_size)
            .limit(page_size)
            .order_by(cls.created_at.desc())
        )
        return list(result.scalars().all())
