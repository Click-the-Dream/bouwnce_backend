from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Self
from uuid import UUID as UUID_Type

from sqlalchemy import DateTime, ForeignKey, String, select
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.basemodel import BaseModel

if TYPE_CHECKING:
    from app.models import User


class WebPushSubscription(BaseModel):
    """A browser Web Push subscription (endpoint + encryption keys).

    One row per browser/device subscription. A user may hold several rows
    (one per browser). ``endpoint`` uniquely identifies a subscription.
    """

    __tablename__ = "web_push_subscriptions"

    user_id: Mapped[UUID_Type] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    endpoint: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    p256dh: Mapped[str] = mapped_column(String, nullable=False)
    auth: Mapped[str] = mapped_column(String, nullable=False)
    expiration_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

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
        expiration_time: datetime | None = None,
    ) -> Self:
        result = await db.execute(select(cls).where(cls.endpoint == endpoint))
        row = result.scalar_one_or_none()
        if row is None:
            row = cls(
                user_id=user_id,
                endpoint=endpoint,
                p256dh=p256dh,
                auth=auth,
                expiration_time=expiration_time,
            )
            db.add(row)
        else:
            row.user_id = user_id
            row.p256dh = p256dh
            row.auth = auth
            row.expiration_time = expiration_time
        await db.flush()
        await db.refresh(row)
        return row

    @classmethod
    async def list_for_user(cls, db: AsyncSession, user_id: UUID_Type) -> list[Self]:
        result = await db.execute(
            select(cls).where(cls.user_id == user_id).order_by(cls.created_at)
        )
        return list(result.scalars().all())

    @classmethod
    async def delete_by_endpoint(
        cls, db: AsyncSession, *, user_id: UUID_Type, endpoint: str
    ) -> bool:
        """Remove a subscription owned by ``user_id``. Returns False if absent."""
        result = await db.execute(select(cls).where(cls.endpoint == endpoint))
        row = result.scalar_one_or_none()
        if row is None or str(row.user_id) != str(user_id):
            return False
        await db.delete(row)
        await db.flush()
        return True
