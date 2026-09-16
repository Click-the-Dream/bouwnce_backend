import asyncio
import logging
from datetime import UTC, datetime, timedelta

import redis.asyncio as aioredis
from sqlalchemy import select

from app.core.config import settings
from app.db.postgres_db_conn import get_async_session
from app.event_broadcast.models.attendance import UserEventAttendance
from app.models.order import Order
from app.schemas.events import PaidOrderEvent
from app.service.payment.paystack import paystack_service
from app.worker.celery_app import celery_app
from app.worker.event_system import (
    EventAttendancePaymentCompletedEvent,
    EventNames,
    dispatch_event,
)
from app.worker.tasks.order_processor import process_paid_order

logger = logging.getLogger(__name__)


async def reconcile_pending_event_payments() -> int:
    pool = aioredis.ConnectionPool.from_url(
        settings.REDIS_URL, decode_responses=True, max_connections=2
    )
    redis = aioredis.Redis(connection_pool=pool)
    reconciled = 0
    try:
        async with get_async_session() as db:
            result = await db.execute(
                select(UserEventAttendance)
                .where(
                    UserEventAttendance.payment_status == "pending",
                    UserEventAttendance.payment_reference.is_not(None),
                    UserEventAttendance.created_at
                    >= datetime.now(UTC) - timedelta(days=1),
                    UserEventAttendance.is_deleted.is_(False),
                )
                .order_by(UserEventAttendance.created_at.asc())
                .limit(100)
            )
            attendances = list(result.scalars().all())
            for attendance in attendances:
                try:
                    paid, payload = await asyncio.to_thread(
                        paystack_service.callback, attendance.payment_reference
                    )
                    if not paid:
                        continue
                    await dispatch_event(
                        EventNames.EVENT_ATTENDANCE_PAYMENT_COMPLETED,
                        EventAttendancePaymentCompletedEvent(
                            attendance_id=str(attendance.id),
                            reference=attendance.payment_reference,
                            amount_kobo=int(payload.get("amount", 0)),
                        ),
                        db=db,
                        redis=redis,
                    )
                    reconciled += 1
                except Exception:
                    logger.exception(
                        "Unable to reconcile event payment attendance_id=%s",
                        attendance.id,
                    )
    finally:
        await redis.aclose()
    return reconciled


async def reconcile_pending_order_payments() -> int:
    reconciled = 0
    async with get_async_session() as db:
        result = await db.execute(
            select(Order)
            .where(
                Order.status.in_(["initiated", "abandoned"]),
                Order.created_at >= datetime.now(UTC) - timedelta(days=1),
                Order.is_deleted.is_(False),
            )
            .order_by(Order.created_at.asc())
            .limit(100)
        )
        orders = list(result.scalars().all())
        for order in orders:
            try:
                paid, payload = await asyncio.to_thread(
                    paystack_service.callback, order.reference_token
                )
                if not paid:
                    continue
                amount_kobo = int(payload.get("amount", 0))
                process_paid_order.delay(
                    PaidOrderEvent(
                        event_id=str(payload.get("id") or order.id),
                        reference=order.reference_token,
                        amount=amount_kobo,
                    ).model_dump(mode="json")
                )
                reconciled += 1
            except Exception:
                logger.exception(
                    "Unable to reconcile order payment order_id=%s", order.id
                )
    return reconciled


@celery_app.task(name="app.worker.tasks.event_payment_reconciliation.reconcile")
def reconcile() -> int:
    async def _run() -> int:
        event_count = await reconcile_pending_event_payments()
        order_count = await reconcile_pending_order_payments()
        return event_count + order_count

    return asyncio.run(_run())
