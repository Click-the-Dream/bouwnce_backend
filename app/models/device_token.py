from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Self
from uuid import UUID as UUID_Type

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func, select
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.basemodel import BaseModel

if TYPE_CHECKING:
    from app.models import User


class DeviceToken(BaseModel):
    __tablename__ = "device_tokens"

    user_id: Mapped[UUID_Type] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token: Mapped[str] = mapped_column(String, nullable=False)
    platform: Mapped[str] = mapped_column(String, nullable=False, default="unknown")
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(lazy="joined")

    __table_args__ = (
        UniqueConstraint("user_id", "token", name="uix_user_device_token"),
    )

    @classmethod
    async def upsert(
        cls, db: AsyncSession, *, user_id: UUID_Type, token: str, platform: str
    ) -> Self:
        result = await db.execute(
            select(cls).where(cls.user_id == user_id, cls.token == token)
        )
        row = result.scalar_one_or_none()
        if row is None:
            row = cls(user_id=user_id, token=token, platform=platform)
            db.add(row)
        else:
            row.platform = platform
            row.last_seen_at = datetime.utcnow()
        await db.flush()
        await db.refresh(row)
        return row
