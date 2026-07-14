from __future__ import annotations

from datetime import datetime
from enum import Enum as PyEnum
from typing import TYPE_CHECKING, Self

from sqlalchemy import UUID, DateTime, Enum, Float, String, Table, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.matching_ground.model.interest import Interest
from app.models.basemodel import BaseModel

if TYPE_CHECKING:
    from app.models.user import User


class EventState(PyEnum):
    DRAFT = "draft"
    LIVE = "live"


user_outing_events = Table(
    "user_outing_events",
    BaseModel.metadata,
    mapped_column("user_id", UUID, primary_key=True),
    mapped_column("outing_event_id", UUID, primary_key=True),
)


class OutingEvent(BaseModel):
    __tablename__ = "outing_events"

    name: Mapped[str] = mapped_column(String, nullable=False)
    desc: Mapped[str] = mapped_column(String, nullable=False)
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    location: Mapped[str] = mapped_column(String, nullable=False)
    link: Mapped[str] = mapped_column(String, nullable=False)
    banner_url: Mapped[str] = mapped_column(String, nullable=False)
    state: Mapped[EventState] = mapped_column(
        Enum(EventState, name="event_state"), nullable=False
    )

    event_interests: Mapped[list[Interest]] = relationship(
        back_populates="outing_event", secondary="outing_event_interests"
    )
    users: Mapped[list[User]] = relationship(
        back_populates="outing_events", secondary="user_outing_events", viewonly=True
    )

    @classmethod
    async def create_event(cls, db: AsyncSession, event_data: dict) -> True:

        query = (
            insert(cls)
            .values(event_data)
            .on_conflict_do_nothing(index_elements=["name"])
        )
        await db.execute(query)
        await db.commit()

        return True

    @classmethod
    async def paginate_events(
        cls, db: AsyncSession, page: int, page_size: int
    ) -> list[Self]:
        offset = (page - 1) * page_size
        stmt = select(cls).offset(offset).limit(page_size)
        result = await db.execute(stmt)

        return list(result.scalars().all())

    @classmethod
    async def get_event_by_id(cls, db: AsyncSession, event_id: str) -> Self | None:
        stmt = select(cls).where(cls.id == event_id)
        result = await db.execute(stmt)

        return result.scalar_one_or_none()

    @classmethod
    async def add_user_to_event(
        cls, db: AsyncSession, user_id: str, event_id: str
    ) -> bool:

        stmt = (
            insert(user_outing_events)
            .values(user_id=user_id, outing_event_id=event_id)
            .on_conflict_do_nothing()
        )

        await db.execute(stmt)
        await db.commit()

        return True

    @classmethod
    async def remove_user_from_event(
        cls, db: AsyncSession, user_id: str, event_id: str
    ) -> bool:

        stmt = user_outing_events.delete().where(
            user_outing_events.c.user_id == user_id,
            user_outing_events.c.outing_event_id == event_id,
        )

        await db.execute(stmt)
        await db.commit()

        return True

    @staticmethod
    async def get_users_for_event(db: AsyncSession, event_id: str) -> list[User]:
        stmt = (
            select(User)
            .join(user_outing_events)
            .where(user_outing_events.c.outing_event_id == event_id)
        )
        result = await db.execute(stmt)

        return list(result.scalars().all())

    async def delete(self, db: AsyncSession) -> bool:
        await db.delete(self)
        await db.commit()

        return True
