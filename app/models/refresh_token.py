from datetime import datetime
from typing import Self

from sqlalchemy import Column, DateTime, ForeignKey, String, func, select
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import relationship

from app.models.basemodel import BaseModel


class RefreshToken(BaseModel):
    __tablename__ = "refresh_tokens"

    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token = Column(String, nullable=False, unique=True)
    device_id = Column(String, nullable=False, unique=True)
    user_agent = Column(String, nullable=False)
    ip_address = Column(String, nullable=False)
    issued_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)

    user = relationship("User", back_populates="refresh_tokens", uselist=False)

    @classmethod
    async def get_token_by_user_and_device(
        cls, user_id: str, device_id: str, db: AsyncSession
    ) -> Self | None:

        stmt = select(cls).where(cls.user_id == user_id, cls.device_id == device_id)
        result = await db.execute(stmt)

        return result.scalar_one_or_none()

    async def revoke(self, db: AsyncSession) -> None:
        """
        Revoke the refresh token for a specific user and device.
        """
        await self.delete(db)

    @classmethod
    async def create_refresh_token(
        cls,
        user_id: str,
        token: str,
        device_id: str,
        user_agent: str,
        ip_address: str,
        expires_at: datetime,
        db: AsyncSession,
    ):
        existing_token = await cls.get_token_by_user_and_device(user_id, device_id, db)
        if existing_token:
            await existing_token.revoke(db)

        refresh_token = await cls.create(
            {
                "user_id": user_id,
                "token": token,
                "device_id": device_id,
                "user_agent": user_agent,
                "ip_address": ip_address,
                "expires_at": expires_at,
            },
            db,
        )

        return refresh_token
