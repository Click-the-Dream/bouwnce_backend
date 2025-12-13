from datetime import UTC, datetime, timedelta

from sqlalchemy import Column, String, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.basemodel import BaseModel


class Waitlist(BaseModel):
    __tablename__ = "waitlists"

    email = Column(String, unique=True, nullable=False)
    full_name = Column(String, nullable=False)
    phone_number = Column(String, nullable=False)
    institution = Column(String, nullable=False)

    @classmethod
    async def get_today_count(cls, db: AsyncSession) -> int:

        now = datetime.now(UTC)
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)

        smt = (
            select(func.count())
            .select_from(cls)
            .where(cls.created_at >= start)
            .where(cls.created_at < end)
        )
        result = await db.execute(smt)
        count = result.scalar_one()

        return count
