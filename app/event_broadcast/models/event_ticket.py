from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Self

from sqlalchemy import UUID, DateTime, Float, ForeignKey, String, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship, selectinload

from app.models.basemodel import BaseModel

if TYPE_CHECKING:
    from app.event_broadcast.models.attendance import UserEventAttendance
    from app.event_broadcast.models.events import OutingEvent
    from app.models.user import User


class EventTicket(BaseModel):
    """One purchased ticket unit, identified by its unique 10-digit code."""

    __tablename__ = "event_tickets"

    attendance_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user_event_attendance.id"), nullable=False
    )
    event_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("outing_events.id"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    ticket_name: Mapped[str] = mapped_column(String, nullable=False)
    code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    unit_amount: Mapped[float] = mapped_column(Float, nullable=False)
    qr_code_url: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="valid")
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    used_by: Mapped[str | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    attendance: Mapped[UserEventAttendance] = relationship(
        "UserEventAttendance",
        foreign_keys=[attendance_id],
        primaryjoin="EventTicket.attendance_id == UserEventAttendance.id",
    )
    event: Mapped[OutingEvent] = relationship(
        "OutingEvent",
        foreign_keys=[event_id],
        primaryjoin="EventTicket.event_id == OutingEvent.id",
    )
    user: Mapped[User] = relationship(
        "User",
        foreign_keys=[user_id],
        primaryjoin="EventTicket.user_id == User.id",
    )

    @classmethod
    async def create_tickets(cls, db: AsyncSession, tickets: list[dict]) -> list[Self]:
        """Insert ticket rows; collisions on ``code`` are silently skipped so a
        retried fulfillment can never mint duplicate rows for the same codes."""
        rows = [cls(**ticket) for ticket in tickets]
        db.add_all(rows)
        await db.flush()
        return rows

    @classmethod
    async def get_by_code(
        cls, db: AsyncSession, code: str, *, with_attendance: bool = False
    ) -> Self | None:
        stmt = select(cls).where(cls.code == code, cls.is_deleted.is_(False))
        if with_attendance:
            from app.event_broadcast.models.attendance import UserEventAttendance

            stmt = stmt.options(
                selectinload(cls.attendance).selectinload(UserEventAttendance.user),
                selectinload(cls.event),
            )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @classmethod
    async def get_by_attendance_id(
        cls, db: AsyncSession, attendance_id: str
    ) -> list[Self]:
        result = await db.execute(
            select(cls).where(
                cls.attendance_id == attendance_id, cls.is_deleted.is_(False)
            )
        )
        return list(result.scalars().all())

    @classmethod
    async def get_user_tickets(
        cls,
        db: AsyncSession,
        user_id: str,
        page: int,
        page_size: int,
        event_id: str | None = None,
        status: str | None = None,
    ) -> dict:
        from app.event_broadcast.models.events import OutingEvent

        filters = [cls.user_id == user_id, cls.is_deleted.is_(False)]
        if event_id:
            filters.append(cls.event_id == event_id)
        if status:
            filters.append(cls.status == status)

        query = (
            select(cls)
            .join(OutingEvent, cls.event_id == OutingEvent.id)
            .where(*filters)
            .options(selectinload(cls.event))
            .order_by(cls.created_at.desc())
        )

        count_query = select(func.count()).select_from(cls).where(*filters)

        count_result = await db.execute(count_query)
        total = count_result.scalar() or 0

        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await db.execute(query)
        tickets = list(result.scalars().all())

        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0

        return {
            "tickets": tickets,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }

    @classmethod
    async def claim_for_verification(
        cls,
        db: AsyncSession,
        code: str,
        event_id: str,
        verifier_id: str,
        used_at: datetime,
    ) -> bool:
        """Atomically mark a valid ticket as used.

        Single conditional UPDATE: two concurrent verify calls for the same
        code can never both succeed — the second sees ``status != 'valid'``
        and returns False. Scoped to ``event_id`` so a code can only ever be
        claimed for its own event. Caller commits.
        """
        result = await db.execute(
            update(cls)
            .where(
                cls.code == code,
                cls.event_id == event_id,
                cls.status == "valid",
                cls.is_deleted.is_(False),
            )
            .values(status="used", used_at=used_at, used_by=verifier_id)
            .execution_options(synchronize_session=False)
        )
        return result.rowcount == 1

    @classmethod
    async def count_codes_existing(cls, db: AsyncSession, codes: list[str]) -> set[str]:
        """Return the subset of ``codes`` that already exist (collision check)."""
        if not codes:
            return set()
        result = await db.execute(select(cls.code).where(cls.code.in_(codes)))
        return {row for row in result.scalars().all()}

    def to_public_dict(self) -> dict[str, Any]:
        data = self.to_dict()
        for key in ("id", "attendance_id", "event_id", "user_id", "used_by"):
            if data.get(key) is not None:
                data[key] = str(data[key])
        return data
