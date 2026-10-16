from __future__ import annotations

from typing import TYPE_CHECKING, Self

from sqlalchemy import ForeignKey, Integer, UniqueConstraint, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.basemodel import BaseModel

if TYPE_CHECKING:
    from app.event_broadcast.models.attendance import UserEventAttendance
    from app.event_broadcast.models.events import OutingEvent


class EventReminderLog(BaseModel):
    """One row per (event, attendance, reminder window) already claimed/sent.

    The unique constraint is the dedup anchor for the scheduled reminder job:
    a window is claimed with INSERT ... ON CONFLICT DO NOTHING before
    dispatching, so concurrent worker runs can never double-send a window.
    """

    __tablename__ = "event_reminder_log"
    __table_args__ = (
        UniqueConstraint(
            "attendance_id",
            "event_id",
            "window",
            name="uq_event_reminder_log_attendance_event_window",
        ),
    )

    event_id: Mapped[str] = mapped_column(
        ForeignKey("outing_events.id"), nullable=False, index=True
    )
    attendance_id: Mapped[str] = mapped_column(
        ForeignKey("user_event_attendance.id"), nullable=False, index=True
    )
    # How many days before the event start this reminder covers (e.g. 7, 3, 2, 1).
    window: Mapped[int] = mapped_column(Integer, nullable=False)
    is_sent: Mapped[bool] = mapped_column(default=False, nullable=False)

    event: Mapped[OutingEvent] = relationship(
        "OutingEvent",
        foreign_keys=[event_id],
        primaryjoin="EventReminderLog.event_id == OutingEvent.id",
        viewonly=True,
    )
    attendance: Mapped[UserEventAttendance] = relationship(
        "UserEventAttendance",
        foreign_keys=[attendance_id],
        primaryjoin="EventReminderLog.attendance_id == UserEventAttendance.id",
        viewonly=True,
    )

    @classmethod
    async def claim_windows(
        cls,
        db: AsyncSession,
        claims: list[dict],
    ) -> list[Self]:
        """Insert claim rows, skipping ones already claimed (ON CONFLICT DO NOTHING).

        Each claim dict needs ``event_id``, ``attendance_id`` and ``window``.
        Returns the rows inserted by THIS call only — pre-existing claims are
        filtered out, so the caller never re-dispatches a deduped window.
        """
        if not claims:
            return []

        result = await db.execute(
            pg_insert(cls)
            .values(claims)
            .on_conflict_do_nothing(
                constraint="uq_event_reminder_log_attendance_event_window"
            )
            .returning(cls.id)
        )
        inserted_ids = {str(row.id) for row in result.all()}
        await db.flush()

        # RETURNING gives us exactly the rows this call inserted; re-selecting
        # them keeps the ORM identity map consistent for the caller.
        if not inserted_ids:
            return []
        rows = await db.execute(select(cls).where(cls.id.in_(inserted_ids)))
        return list(rows.scalars().all())
