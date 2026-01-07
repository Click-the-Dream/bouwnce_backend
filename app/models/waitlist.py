from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import String, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.models import BaseModel


class Waitlist(BaseModel):
    __tablename__ = "waitlists"

    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    phone_number: Mapped[str] = mapped_column(String, nullable=False)
    institution: Mapped[str] = mapped_column(String, nullable=False)

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

    @classmethod
    async def group_by_institution(
        cls, db: AsyncSession, page: int = 1, page_size: int = 10
    ) -> dict[str, Any]:

        smt = (
            select(cls.institution, func.count().label("count"))
            .group_by(cls.institution)
            .order_by(cls.institution)
        )

        offset = (page - 1) * page_size

        smt = smt.offset(offset).limit(page_size)
        result = await db.execute(smt)

        result = result.all()

        count_query = select(func.count()).select_from(cls)
        count_result = await db.execute(count_query)
        count = count_result.scalar() or 0

        data = {institute: count for institute, count in result}
        return {
            "institutions": data,
            "page": page,
            "page_size": page_size,
            "total": count,
        }
