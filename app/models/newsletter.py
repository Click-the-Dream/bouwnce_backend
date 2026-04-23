from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, DateTime, select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Self
from datetime import datetime

from app.models.basemodel import BaseModel


class NewsLetter(BaseModel):
    __tablename__ = "newsletters"
    
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    description: Mapped[str] = mapped_column(String, nullable=False)
    subject: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(String, nullable=False)
    is_sent: Mapped[bool] = mapped_column(nullable=False, default=False)
    send_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="scheduled")
    
    @classmethod
    async def get_by_name(cls, db: AsyncSession, name: str) -> Self | None:
        result = await db.execute(select(cls).where(cls.name == name))
        return result.scalar_one_or_none()
    