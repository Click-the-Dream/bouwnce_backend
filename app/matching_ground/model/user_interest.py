from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID as UUID_PK

from sqlalchemy import ForeignKey, Index, UniqueConstraint, delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship, selectinload

from app.matching_ground.model.interest import Interest
from app.models.basemodel import BaseModel
from app.utils.exception import BadRequestException

if TYPE_CHECKING:
    from app.models.user import User


class UserInterest(BaseModel):
    __tablename__ = "user_interests"

    user_id: Mapped[UUID_PK] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    interest_id: Mapped[UUID_PK] = mapped_column(
        ForeignKey("interests.id"), primary_key=True
    )

    user: Mapped[User] = relationship(back_populates="user_interest")
    interest: Mapped[Interest] = relationship(back_populates="user_interest")

    __table_args__ = (
        UniqueConstraint("user_id", "interest_id"),
        Index("idx_user_interest", "user_id", "interest_id"),
    )

    @classmethod
    async def get_user_interests(cls, db: AsyncSession, user_id: str) -> list[Interest]:
        query = (
            select(cls)
            .where(cls.user_id == user_id)
            .options(selectinload(cls.interest))
        )
        result = await db.execute(query)
        return [row.interest for row in result.scalars().all()]

    @classmethod
    async def add_user_interest(
        cls, db: AsyncSession, user_id: str, interests: list[str]
    ) -> bool:
        query = select(Interest.id).where(Interest.name.in_(interests))
        interest_result = await db.execute(query)

        interest_ids = interest_result.scalars().all()

        data = [
            {"user_id": user_id, "interest_id": interest_id}
            for interest_id in interest_ids
        ]

        query = (
            insert(cls)
            .values(data)
            .on_conflict_do_nothing(index_elements=["user_id", "interest_id"])
        )

        await db.execute(query)
        return True

    @classmethod
    async def replace_user_interests(
        cls, db: AsyncSession, user_id: str, interests: list[str]
    ) -> bool:
        normalized = list(
            dict.fromkeys(name.strip() for name in interests if name.strip())
        )
        result = await db.execute(
            select(Interest.id, Interest.name).where(Interest.name.in_(normalized))
        )
        rows = result.all()
        found_names = {name for _, name in rows}
        unknown = sorted(set(normalized) - found_names)
        if unknown:
            raise BadRequestException(f"Unknown interests: {', '.join(unknown)}")

        await db.execute(delete(cls).where(cls.user_id == user_id))
        if rows:
            await db.execute(
                insert(cls).values(
                    [
                        {"user_id": user_id, "interest_id": interest_id}
                        for interest_id, _ in rows
                    ]
                )
            )
        await db.commit()
        return True

    @classmethod
    async def remove_user_interests(
        cls, db: AsyncSession, user_id: str, interest_ids: list[str]
    ) -> bool:

        query = delete(cls).where(
            cls.user_id == user_id, cls.interest_id.in_(interest_ids)
        )

        await db.execute(query)
        return True
