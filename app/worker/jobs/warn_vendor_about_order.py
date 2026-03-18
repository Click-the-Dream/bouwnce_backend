from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, select
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.db.postgres_db_conn import get_async_session
from app.models.suborder import SubOrder
from app.worker.tasks.email import send_email_using_worker


async def warn_vendor_to_accept_order():
    try:
        now = datetime.now(UTC)
        yesterday = now - timedelta(days=1)
        decline_threshold = now - timedelta(days=4)  # > 4 days old → decline

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

                # --- AUTO DECLINE ---
                if suborder.updated_at <= decline_threshold:
                    # TODO:
                    # 1) decline order
                    # 2) send decline email
                    # 3) mark auto_declined_at
                    continue

                # --- WARNING EMAIL ---
                else:
                    remaining_days = max(0, 4 - age.days)

                    email_template_name = "vendor_follow_up_order.html"

                    context = {
                        "project_name": settings.PROJECT_NAME,
                        "store_name": store.name,
                        "auto_decline_time": remaining_days,
                        "dashboard": "#",
                    }

                    subject = "You Have Unattended Orders"

                    send_email_using_worker.delay(
                        email_to=store.email,
                        subject=subject,
                        context=context,
                        template_name=email_template_name,
                    )
    except Exception as e:
        print("Error occured while warning vendor about not reviewed order: ", str(e))
