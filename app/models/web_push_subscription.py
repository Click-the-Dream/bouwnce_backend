from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Self
from uuid import UUID as UUID_Type

from sqlalchemy import DateTime, ForeignKey, String, func, select
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.basemodel import BaseModel

if TYPE_CHECKING:
    from app.models import User


class WebPushSubscription(BaseModel):
    __tablename__ = "web_push_subscriptions"

    user_id: Mapped[UUID_Type] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # A browser PushSubscription endpoint is globally unique per browser profile,
    # so it is the natural identity for a web push subscription row.
    endpoint: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    p256dh: Mapped[str] = mapped_column(String(256), nullable=False)
    auth: Mapped[str] = mapped_column(String(128), nullable=False)
    expiration_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), nullable=False
    )
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)

    user: Mapped[User] = relationship(lazy="joined")

    @classmethod
    async def upsert(
        cls,
        db: AsyncSession,
        *,
        user_id: UUID_Type,
        endpoint: str,
        p256dh: str,
        auth: str,
        expiration_time: datetime | None,
        user_agent: str | None = None,
    ) -> Self:
        result = await db.execute(
            select(cls).where(cls.user_id == user_id, cls.endpoint == endpoint)
        )
        row = result.scalar_one_or_none()
        if row is None:
            row = cls(
                user_id=user_id,
                endpoint=endpoint,
                p256dh=p256dh,
                auth=auth,
                expiration_time=expiration_time,
                user_agent=user_agent,
            )
            db.add(row)
        else:
            # Keys can rotate on re-subscription; refresh them in place.
            row.p256dh = p256dh
            row.auth = auth
            row.expiration_time = expiration_time
            row.user_agent = user_agent
            row.last_seen_at = datetime.now(UTC)
        await db.flush()
        await db.refresh(row)
        return row

    @classmethod
    async def delete_for_user(
        cls, db: AsyncSession, *, user_id: UUID_Type, endpoint: str
    ) -> bool:
        result = await db.execute(
            select(cls).where(cls.user_id == user_id, cls.endpoint == endpoint)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return False
        await db.delete(row)
        await db.flush()
        return True

    @classmethod
    async def list_for_user(cls, db: AsyncSession, *, user_id: UUID_Type) -> list[Self]:
        result = await db.execute(select(cls).where(cls.user_id == user_id))
        return list(result.scalars().all())
