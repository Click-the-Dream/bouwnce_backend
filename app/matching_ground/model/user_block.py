import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.basemodel import BaseModel


class UserBlock(BaseModel):
    __tablename__ = "user_blocks"
    __table_args__ = (UniqueConstraint("blocker_user_id", "blocked_user_id", name="uq_user_blocks_pair"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    blocker_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    blocked_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    
    
    @classmethod
    async def is_blocked_between(cls, session: AsyncSession, user_a: uuid.UUID, user_b: uuid.UUID) -> bool:
        result = await session.execute(
            select(cls.id).where(
                or_(
                    and_(cls.blocker_user_id == user_a, cls.blocked_user_id == user_b),
                    and_(cls.blocker_user_id == user_b, cls.blocked_user_id == user_a),
                )
            )
        )
        return result.scalar_one_or_none() is not None
