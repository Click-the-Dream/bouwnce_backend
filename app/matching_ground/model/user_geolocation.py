import uuid
from datetime import UTC, datetime
from typing import Self

from sqlalchemy import DateTime, Float, ForeignKey, select
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.basemodel import BaseModel


class UserGeolocation(BaseModel):
    __tablename__ = "user_geolocations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.now(UTC)
    )

    user = relationship("User", back_populates="geolocation")

    @classmethod
    async def get_by_user_id(
        cls, session: AsyncSession, user_id: uuid.UUID
    ) -> Self | None:
        result = await session.execute(select(cls).where(cls.user_id == user_id))
        return result.scalar_one_or_none()

    @classmethod
    async def upsert(
        cls, session: AsyncSession, user_id: uuid.UUID, lat: float, lon: float
    ) -> Self:
        row = await cls.get_by_user_id(session, user_id)
        if row is None:
            row = cls(user_id=user_id, lat=lat, lon=lon)
            session.add(row)
        else:
            row.lat = lat
            row.lon = lon
        await session.flush()
        return row

    @classmethod
    async def list_others(cls, session: AsyncSession, user_id: uuid.UUID) -> list[Self]:
        result = await session.execute(select(cls).where(cls.user_id != user_id))
        return list(result.scalars().all())
