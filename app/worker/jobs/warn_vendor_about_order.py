from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, select
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.db.postgres_db_conn import get_async_session
from app.db.redis import get_redis_client
from app.models.suborder import SubOrder
from app.worker.event_system import (
    EmailNotificationEvent,
    EventNames,
    SubOrderCancelEvent,
    dispatch_event,
)


async def warn_vendor_to_accept_order():
    try:
        now = datetime.now(UTC)
        yesterday = now - timedelta(days=1)
        decline_threshold = now - timedelta(days=3)  # > 3 days old → cancel
        redis = await get_redis_client()

        async with get_async_session() as db:

            stmt = (
                select(SubOrder)
                .options(selectinload(SubOrder.store))
                .where(
                    and_(
                        SubOrder.updated_at <= yesterday,  # older than 24h
                        SubOrder.status == "paid",
                    )
                )
            )

            result = await db.execute(stmt)
            suborders = result.scalars().all()

            for suborder in suborders:
                store = suborder.store
                age = now - suborder.updated_at

                # --- AUTO CANCEL ---
                if suborder.updated_at <= decline_threshold:
                    await dispatch_event(
                        EventNames.SUBORDER_CANCEL,
                        SubOrderCancelEvent(suborder_id=str(suborder.id)),
                        db=db,
                        redis=redis,
                    )

                    await dispatch_event(
                        EventNames.EMAIL_NOTIFICATION,
                        EmailNotificationEvent(
                            email_to=store.email,
                            subject="Order Auto Cancelled",
                            context={
                                "project_name": settings.PROJECT_NAME,
                                "store_name": store.name,
                                "dashboard": "#",
                            },
                            template_name="vendor_follow_up_order.html",
                        ),
                        db=db,
                        redis=redis,
                    )
                    continue

                # --- WARNING EMAIL ---
                else:
                    remaining_days = max(0, 3 - age.days)

                    email_template_name = "vendor_follow_up_order.html"

                    context = {
                        "project_name": settings.PROJECT_NAME,
                        "store_name": store.name,
                        "auto_decline_time": remaining_days,
                        "dashboard": "#",
                    }

                    subject = "You Have Unattended Orders"

                    await dispatch_event(
                        EventNames.EMAIL_NOTIFICATION,
                        EmailNotificationEvent(
                            email_to=store.email,
                            subject=subject,
                            context=context,
                            template_name=email_template_name,
                        ),
                        db=db,
                        redis=redis,
                    )
    except Exception as e:
        print("Error occured while warning vendor about not reviewed order: ", str(e))
