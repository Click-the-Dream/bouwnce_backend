"""Event reminder domain logic.

Pure decision logic (due windows, per-send content) lives here so it can be
unit-tested without Redis, Celery, or the database. I/O orchestration lives in
``app.worker.tasks.event_reminder``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.event_broadcast.models.attendance import UserEventAttendance
from app.event_broadcast.models.events import EventState, OutingEvent
from app.event_broadcast.models.reminder import EventReminderLog


@dataclass(frozen=True)
class ReminderContent:
    """Channel-agnostic reminder copy for one (event, window) pair."""

    title: str
    body: str
    email_subject: str
    days_before: int


def parse_reminder_windows(raw: str) -> list[int]:
    """Parse the comma-separated day windows, sorted descending, no dupes/zeros.

    Invalid segments are skipped rather than raising: a bad env value must not
    500 app config loading, and a job silently searching zero valid windows
    will surface loudly in the logs on every run.
    """
    windows: list[int] = []
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            value = int(chunk)
        except ValueError:
            continue
        if value > 0 and value not in windows:
            windows.append(value)
    return sorted(windows, reverse=True)


def due_windows(
    event_date: datetime, now: datetime, windows: list[int] | None = None
) -> list[int]:
    """Which reminder windows for this event are due as of ``now``.

    A window W is due iff ``now >= event_date - W days`` and the event has not
    started yet. Shared timezone convention as the existing event queries:
    naive-UTC ``date`` column compared against ``datetime.now(UTC)``.
    """
    windows = (
        windows
        if windows is not None
        else parse_reminder_windows(settings.EVENT_REMINDER_WINDOWS_DAYS)
    )
    if event_date <= now:
        return []
    return [
        w
        for w in sorted(windows, reverse=True)
        if event_date - timedelta(days=w) <= now
    ]


def reminder_content(event: OutingEvent, window: int) -> ReminderContent:
    """Build the shared copy for one channel dispatch."""
    days = max(window, 0)
    when = "today" if days == 0 else f"in {days} day{'s' if days != 1 else ''}"
    title = f"{event.name} starts {when}"
    body = (
        f"Don't forget: {event.name} starts {when} at {event.location}. "
        "See you there!"
    )
    subject = f"Reminder: {event.name} starts {when}"
    return ReminderContent(
        title=title, body=body, email_subject=subject, days_before=window
    )


@dataclass(frozen=True)
class ReminderCandidate:
    """One (event, attendance) pair that has at least one due window."""

    event: OutingEvent
    attendance: UserEventAttendance
    windows: list[int]


async def find_due_reminder_candidates(
    db: AsyncSession, now: datetime
) -> list[ReminderCandidate]:
    """Select paid, non-deleted attendees of live upcoming events, paired with
    their due windows (minus windows already claimed in event_reminder_log).

    One pass over the widest window's range; the due filter per event is
    applied in Python so the domain rule stays in one place and stays
    unit-testable.
    """
    windows = parse_reminder_windows(settings.EVENT_REMINDER_WINDOWS_DAYS)
    if not windows or not settings.EVENT_REMINDER_ENABLED:
        return []

    max_days = max(windows)
    horizon = now + timedelta(days=max_days)

    result = await db.execute(
        select(OutingEvent, UserEventAttendance)
        .join(
            UserEventAttendance,
            UserEventAttendance.event_id == OutingEvent.id,
        )
        .where(
            OutingEvent.is_deleted.is_(False),
            OutingEvent.state == EventState.LIVE.value,
            OutingEvent.date > now,
            OutingEvent.date <= horizon,
            UserEventAttendance.is_deleted.is_(False),
            UserEventAttendance.payment_status == "successful",
        )
        .options(selectinload(UserEventAttendance.user))
        .order_by(OutingEvent.date.asc())
    )
    pairs = result.all()

    if not pairs:
        return []

    event_ids = {str(event.id) for event, _ in pairs}
    sent = await db.execute(
        select(
            EventReminderLog.event_id,
            EventReminderLog.attendance_id,
            EventReminderLog.window,
        ).where(
            EventReminderLog.is_deleted.is_(False),
            EventReminderLog.event_id.in_(event_ids),
        )
    )
    claimed = {
        (str(event_id), str(att_id), int(window))
        for event_id, att_id, window in sent.all()
    }

    candidates: list[ReminderCandidate] = []
    for event, attendance in pairs:
        fresh = [
            w
            for w in due_windows(event.date, now, windows)
            if (str(event.id), str(attendance.id), w) not in claimed
        ]
        if fresh:
            candidates.append(
                ReminderCandidate(event=event, attendance=attendance, windows=fresh)
            )
    return candidates
