from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum as PyEnum
from typing import TYPE_CHECKING, Any, Self

from sqlalchemy import (
    UUID,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    String,
    Table,
    func,
    select,
)
from sqlalchemy.dialects.postgresql import JSONB, insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.basemodel import BaseModel

if TYPE_CHECKING:
    from app.models.user import User


class EventState(PyEnum):
    DRAFT = "draft"
    LIVE = "live"


class LocationType(PyEnum):
    PHYSICAL = "physical"
    VIRTUAL = "virtual"
    HYBRID = "hybrid"


user_outing_events = Table(
    "user_outing_events",
    BaseModel.metadata,
    Column("user_id", UUID, ForeignKey("users.id"), primary_key=True),
    Column("outing_event_id", UUID, ForeignKey("outing_events.id"), primary_key=True),
)


class OutingEvent(BaseModel):
    __tablename__ = "outing_events"

    name: Mapped[str] = mapped_column(String, nullable=False)
    desc: Mapped[str] = mapped_column(String, nullable=False)
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    location: Mapped[str] = mapped_column(String, nullable=False)
    location_type: Mapped[LocationType] = mapped_column(
        Enum(LocationType, name="location_type_enum"), nullable=False
    )
    link: Mapped[str | None] = mapped_column(String, nullable=True)
    banner_url: Mapped[str] = mapped_column(String, nullable=False)
    state: Mapped[EventState] = mapped_column(
        Enum(EventState, name="event_state"), nullable=False
    )
    ticket_info: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONB, nullable=True
    )
    interests: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)

    creator_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )

    creator: Mapped[User] = relationship(
        back_populates="outing_events", foreign_keys=[creator_id]
    )

    attendees: Mapped[list[User]] = relationship(
        secondary="user_outing_events", viewonly=True
    )

    @classmethod
    async def create_event(cls, db: AsyncSession, event_data: dict) -> Self:
        new_event = cls(**event_data)
        db.add(new_event)
        await db.flush()
        await db.refresh(new_event)
        return new_event

    @classmethod
    async def get_events_by_creator(
        cls,
        db: AsyncSession,
        creator_id,
        page: int,
        page_size: int,
        status: str | None = None,
        name: str | None = None,
    ) -> dict:
        query = select(cls).where(
            cls.creator_id == creator_id, cls.is_deleted == False  # noqa: E712
        )

        if status:
            query = query.where(cls.state == status)

        if name:
            query = query.where(cls.name.ilike(f"%{name}%"))

        query = query.order_by(cls.created_at.desc())

        count_query = (
            select(func.count())
            .select_from(cls)
            .where(cls.creator_id == creator_id, cls.is_deleted == False)  # noqa: E712
        )
        if status:
            count_query = count_query.where(cls.state == status)
        if name:
            count_query = count_query.where(cls.name.ilike(f"%{name}%"))

        count_result = await db.execute(count_query)
        total = count_result.scalar() or 0

        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await db.execute(query)
        events = list(result.scalars().all())

        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0

        return {
            "events": events,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }

    @classmethod
    async def get_event_by_id(cls, db: AsyncSession, event_id) -> Self | None:
        stmt = select(cls).where(
            cls.id == event_id, cls.is_deleted.is_(False)
        )  # noqa: E712
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @classmethod
    async def update_event(cls, db: AsyncSession, event_id, update_data: dict) -> Self:
        stmt = select(cls).where(
            cls.id == event_id, cls.is_deleted.is_(False)
        )  # noqa: E712
        result = await db.execute(stmt)
        event = result.scalar_one_or_none()

        if not event:
            return None

        for key, value in update_data.items():
            if hasattr(event, key) and key not in ("id", "created_at", "creator_id"):
                setattr(event, key, value)

        await db.flush()
        await db.refresh(event)
        return event

    @classmethod
    async def update_event_status(
        cls, db: AsyncSession, event_id, state: EventState
    ) -> Self | None:
        stmt = select(cls).where(
            cls.id == event_id, cls.is_deleted.is_(False)
        )  # noqa: E712
        result = await db.execute(stmt)
        event = result.scalar_one_or_none()

        if not event:
            return None

        event.state = state
        await db.flush()
        await db.refresh(event)
        return event

    @classmethod
    async def delete_event(cls, db: AsyncSession, event_id) -> Self | None:
        stmt = select(cls).where(
            cls.id == event_id, cls.is_deleted.is_(False)
        )  # noqa: E712
        result = await db.execute(stmt)
        event = result.scalar_one_or_none()

        if not event:
            return None

        event.is_deleted = True
        event.deleted_at = datetime.now(UTC)
        await db.flush()
        await db.refresh(event)
        return event

    @classmethod
    async def add_user_to_event(cls, db: AsyncSession, user_id, event_id) -> bool:
        stmt = (
            insert(user_outing_events)
            .values(user_id=user_id, outing_event_id=event_id)
            .on_conflict_do_nothing()
        )
        await db.execute(stmt)
        await db.commit()
        return True

    @classmethod
    async def remove_user_from_event(cls, db: AsyncSession, user_id, event_id) -> bool:
        stmt = user_outing_events.delete().where(
            user_outing_events.c.user_id == user_id,
            user_outing_events.c.outing_event_id == event_id,
        )
        await db.execute(stmt)
        await db.commit()
        return True

    @staticmethod
    async def get_users_for_event(db: AsyncSession, event_id) -> list[User]:
        from app.models.user import User

        stmt = (
            select(User)
            .join(user_outing_events)
            .where(user_outing_events.c.outing_event_id == event_id)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())
