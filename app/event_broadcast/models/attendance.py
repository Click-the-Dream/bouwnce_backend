from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Self

from sqlalchemy import UUID, Float, ForeignKey, Integer, String, func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.basemodel import BaseModel

if TYPE_CHECKING:
    from app.event_broadcast.models.events import OutingEvent
    from app.models.user import User


class UserEventAttendance(BaseModel):
    __tablename__ = "user_event_attendance"

    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id"), nullable=False
    )
    event_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("outing_events.id"), nullable=False
    )
    ticket_info: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    total_amount: Mapped[float] = mapped_column(Float, nullable=False)
    total_tickets: Mapped[int] = mapped_column(Integer, nullable=False)
    payment_status: Mapped[str] = mapped_column(
        String, nullable=False, default="pending"
    )
    attendance_status: Mapped[str] = mapped_column(
        String, nullable=False, default="confirmed"
    )

    user: Mapped[User] = relationship(foreign_keys=[user_id])
    event: Mapped[OutingEvent] = relationship(foreign_keys=[event_id])

    @classmethod
    async def create_attendance(cls, db: AsyncSession, attendance_data: dict) -> Self:
        new_attendance = cls(**attendance_data)
        db.add(new_attendance)
        await db.flush()
        await db.refresh(new_attendance)
        return new_attendance

    @classmethod
    async def get_user_attendance(
        cls,
        db: AsyncSession,
        user_id: str,
        page: int,
        page_size: int,
        name: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        event_type: str | None = None,
    ) -> dict:
        from app.event_broadcast.models.events import OutingEvent

        query = (
            select(cls)
            .join(OutingEvent, cls.event_id == OutingEvent.id)
            .where(cls.user_id == user_id, cls.is_deleted == False)  # noqa: E712
        )

        if name:
            query = query.where(OutingEvent.name.ilike(f"%{name}%"))

        if date_from:
            query = query.where(OutingEvent.date >= date_from)

        if date_to:
            query = query.where(OutingEvent.date <= date_to)

        if event_type:
            now = datetime.now(UTC)
            if event_type == "past":
                query = query.where(OutingEvent.date < now)
            elif event_type == "upcoming":
                query = query.where(OutingEvent.date >= now)

        query = query.order_by(OutingEvent.date.desc())

        count_query = (
            select(func.count())
            .select_from(cls)
            .join(OutingEvent, cls.event_id == OutingEvent.id)
            .where(cls.user_id == user_id, cls.is_deleted == False)  # noqa: E712
        )

        if name:
            count_query = count_query.where(OutingEvent.name.ilike(f"%{name}%"))
        if date_from:
            count_query = count_query.where(OutingEvent.date >= date_from)
        if date_to:
            count_query = count_query.where(OutingEvent.date <= date_to)
        if event_type:
            now = datetime.now(UTC)
            if event_type == "past":
                count_query = count_query.where(OutingEvent.date < now)
            elif event_type == "upcoming":
                count_query = count_query.where(OutingEvent.date >= now)

        count_result = await db.execute(count_query)
        total = count_result.scalar() or 0

        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await db.execute(query)
        attendances = list(result.scalars().all())

        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0

        return {
            "attendances": attendances,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }

    @classmethod
    async def get_event_attendees(
        cls,
        db: AsyncSession,
        event_id: str,
        page: int,
        page_size: int,
        username: str | None = None,
        interest: str | None = None,
    ) -> dict:
        from app.models.user import User

        query = (
            select(cls)
            .join(User, cls.user_id == User.id)
            .where(cls.event_id == event_id, cls.is_deleted == False)  # noqa: E712
        )

        if username:
            query = query.where(User.username.ilike(f"%{username}%"))

        if interest:
            query = query.where(User.interests.any(name=interest))

        query = query.order_by(cls.created_at.desc())

        count_query = (
            select(func.count())
            .select_from(cls)
            .join(User, cls.user_id == User.id)
            .where(cls.event_id == event_id, cls.is_deleted == False)  # noqa: E712
        )

        if username:
            count_query = count_query.where(User.username.ilike(f"%{username}%"))
        if interest:
            count_query = count_query.where(User.interests.any(name=interest))

        count_result = await db.execute(count_query)
        total = count_result.scalar() or 0

        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await db.execute(query)
        attendances = list(result.scalars().all())

        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0

        return {
            "attendances": attendances,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }

    @classmethod
    async def check_existing_attendance(
        cls, db: AsyncSession, user_id: str, event_id: str
    ) -> Self | None:
        stmt = select(cls).where(
            cls.user_id == user_id,
            cls.event_id == event_id,
            cls.is_deleted == False,  # noqa: E712
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @classmethod
    async def cancel_attendance(
        cls, db: AsyncSession, user_id: str, event_id: str
    ) -> Self | None:
        from datetime import UTC, datetime

        stmt = select(cls).where(
            cls.user_id == user_id,
            cls.event_id == event_id,
            cls.is_deleted == False,  # noqa: E712
        )
        result = await db.execute(stmt)
        attendance = result.scalar_one_or_none()

        if not attendance:
            return None

        attendance.is_deleted = True
        attendance.deleted_at = datetime.now(UTC)
        await db.flush()
        await db.refresh(attendance)
        return attendance
