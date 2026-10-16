"""Scheduled event reminder job.

Beat entry ``send-event-reminders`` (every 15 min) runs ``send_event_reminders``,
which:

1. Selects live upcoming events with paid attendees and their due windows
   (``services.reminder`` owns that logic).
2. Claims each (event, attendance, window) via a unique-constraint
   INSERT ... ON CONFLICT DO NOTHING — the dedup anchor.
3. Dispatches email (Celery queue) and web push (Redis queue, drained by the
   existing 5s ``drain_push_queue`` task), then marks the claims sent.
4. On any failure between claim and mark-sent, the unsent claims are deleted
   so the next run retries; the consequence is at-least-once delivery (a rare
   duplicate beats a lost reminder).

The task owns its own DB/Redis clients (NullPool), mirroring
``event_payment_reconciliation`` and ``web_push`` so it works inside the
Celery worker process.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime

import redis.asyncio as aioredis
from sqlalchemy import delete as sa_delete
from sqlalchemy import update as sa_update

from app.core.config import settings
from app.db.postgres_db_conn import get_async_session
from app.event_broadcast.models.reminder import EventReminderLog
from app.event_broadcast.services.reminder import (
    ReminderCandidate,
    find_due_reminder_candidates,
    reminder_content,
)
from app.worker.celery_app import celery_app
from app.worker.event_system import (
    EventNames,
    PushNotificationEvent,
    dispatch_event,
)
from app.worker.tasks.email import send_email_using_worker

logger = logging.getLogger(__name__)


@dataclass
class _Claimed:
    """A candidate whose reminder windows are atomically claimed in the DB."""

    candidate: ReminderCandidate
    claim_ids: list[str]


async def _claim_due_windows() -> list[_Claimed]:
    """Select due candidates and claim their windows in ONE committed tx."""
    async with get_async_session() as db:
        candidates = await find_due_reminder_candidates(db, datetime.now(UTC))
        if not candidates:
            return []

        claimed: list[_Claimed] = []
        for candidate in candidates:
            rows = await EventReminderLog.claim_windows(
                db,
                claims=[
                    {
                        "event_id": candidate.event.id,
                        "attendance_id": candidate.attendance.id,
                        "window": window,
                    }
                    for window in candidate.windows
                ],
            )
            if rows:
                claimed.append(
                    _Claimed(
                        candidate=candidate,
                        claim_ids=[str(row.id) for row in rows],
                    )
                )
        await db.commit()
        return claimed


async def _release_claims(claim_ids: list[str]) -> None:
    """Delete unsent claims so the next run retries them."""
    if not claim_ids:
        return
    async with get_async_session() as db:
        await db.execute(
            sa_delete(EventReminderLog).where(
                EventReminderLog.id.in_(claim_ids),
                EventReminderLog.is_sent.is_(False),
            )
        )
        await db.commit()


async def _dispatch(redis: aioredis.Redis, claimed: list[_Claimed]) -> int:
    """Dispatch email + push for claimed rows, then mark the claims sent."""
    max_emails = settings.EVENT_REMINDER_MAX_EMAILS_PER_RUN
    emails_sent = 0

    async with get_async_session() as db:
        for item in claimed:
            # Per (event, window) copy; a candidate carries the nearest window
            # first, which drives the day count in the message.
            content = reminder_content(item.candidate.event, item.candidate.windows[0])
            attendance = item.candidate.attendance
            user = attendance.user

            if emails_sent < max_emails:
                date_str = (
                    item.candidate.event.date.isoformat()
                    if item.candidate.event.date
                    else ""
                )
                send_email_using_worker.delay(
                    email_to=user.email,
                    subject=content.email_subject,
                    context={
                        "user_name": user.username or user.full_name,
                        "event_name": item.candidate.event.name,
                        "event_date": date_str,
                        "location": item.candidate.event.location,
                        "days_before": content.days_before,
                        "banner_url": item.candidate.event.banner_url,
                        # Match the OTP email's contact link convention.
                        "contact_link": f"mailto: {settings.PROJECT_EMAIL}",
                    },
                    # Compiled template under build/, matching every other
                    # sender in the codebase (login_verification_email.html,
                    # event_tickets.html, ...).
                    template_name="event_reminder.html",
                )
                emails_sent += 1

            await dispatch_event(
                EventNames.PUSH_NOTIFICATION,
                PushNotificationEvent(
                    user_id=str(attendance.user_id),
                    title=content.title,
                    body=content.body,
                    data={
                        "type": "event.reminder",
                        "event_id": str(item.candidate.event.id),
                        "days_before": content.days_before,
                    },
                ),
                db=db,
                redis=redis,
            )

        await db.execute(
            sa_update(EventReminderLog)
            .where(
                EventReminderLog.id.in_(
                    [cid for item in claimed for cid in item.claim_ids]
                )
            )
            .values(is_sent=True)
        )
        await db.commit()
    return emails_sent


async def _run_cycle_with_redis(redis: aioredis.Redis) -> dict:
    claimed = await _claim_due_windows()
    if not claimed:
        return {"claims": 0, "emails": 0}

    claim_ids = [cid for item in claimed for cid in item.claim_ids]
    try:
        emails = await _dispatch(redis, claimed)
        return {"claims": len(claim_ids), "emails": emails}
    except Exception:
        await _release_claims(claim_ids)
        raise


@celery_app.task(name="app.worker.tasks.event_reminder.send_event_reminders")
def send_event_reminders() -> dict:
    """Celery task: send due event reminders (email + web push)."""
    if not settings.EVENT_REMINDER_ENABLED:
        return {"skipped": True}
    pool = aioredis.ConnectionPool.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        max_connections=2,
    )
    redis = aioredis.Redis(connection_pool=pool)
    try:
        stats = asyncio.run(_run_cycle_with_redis(redis))
        if stats["claims"]:
            logger.info("Event reminder cycle: %s", stats)
        return stats
    except Exception as exc:  # noqa: BLE001 - keep the worker alive on infra errors
        logger.error("Event reminder cycle failed: %s", exc)
        return {"error": str(exc)}
    finally:
        asyncio.run(redis.aclose())
