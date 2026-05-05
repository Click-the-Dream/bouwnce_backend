import asyncio
import json
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal

from app.core.security import genrate_verification_code
from app.db.postgres_db_conn import get_async_session
from app.db.redis import get_redis_client
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.payment import Payment
from app.models.store import Store
from app.models.suborder import SubOrder
from app.schemas.events import PaidOrderEvent
from app.utils.helper import generate_suborder_track_id
from app.worker.celery_app import celery_app
from app.worker.event_system import (
    EmailNotificationEvent,
    EventNames,
    MobileEvent,
    ProductStockUpdateEvent,
    PushNotificationEvent,
    ReservationReleaseEvent,
    StoreWalletCreditEvent,
    UserCartClearEvent,
    dispatch_event,
)


def _naira_to_kobo(amount_naira: float) -> int:
    return int(
        (Decimal(str(amount_naira)) * Decimal("100")).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
    )


async def _process_paid_order(event: PaidOrderEvent) -> None:
    reference = event.reference
    amount = event.amount

    redis = await get_redis_client()
    lock_key = f"order_processing:lock:{reference}"
    queue_key = f"order_processing:queued:{reference}"

    lock_acquired = await redis.set(lock_key, "1", ex=900, nx=True)
    if not lock_acquired:
        return

    try:
        async with get_async_session() as db:
            order = await Order.get_by_reference(reference, db)
            if not order:
                return

            if order.status not in ["initiated", "abandoned"]:
                return

            await dispatch_event(
                EventNames.MOBILE_EVENT,
                MobileEvent(
                    event_name="payment.processing.started",
                    payload={"reference": reference, "order_id": str(order.id), "progress": 5},
                ),
                db=db,
                redis=redis,
            )

            if _naira_to_kobo(order.total_amount) != amount:
                await order.update(db, {"status": "failed"})
                await Payment.update_by_id(str(order.payment_id), {"status": "failed"}, db)
                await dispatch_event(
                    EventNames.MOBILE_EVENT,
                    MobileEvent(
                        event_name="payment.failed",
                        payload={
                            "reference": reference,
                            "order_id": str(order.id),
                            "progress": 100,
                        },
                    ),
                    db=db,
                    redis=redis,
                )
                return

            await dispatch_event(
                EventNames.MOBILE_EVENT,
                MobileEvent(
                    event_name="payment.verified",
                    payload={
                        "reference": reference,
                        "order_id": str(order.id),
                        "progress": 25,
                    },
                ),
                db=db,
                redis=redis,
            )

            user = await Order.fetch_owner_of_order(str(order.user_id), db)
            if not user:
                return

            grouped_products_by_store = order.products

            now = datetime.now(UTC)
            year = now.year

            for store_product in grouped_products_by_store:
                store_id, products_data = next(iter(store_product.items()))
                store = await Store.get_by_id(store_id, db)
                otp = genrate_verification_code()

                suborder_data = {
                    "store_id": store_id,
                    "order_id": order.id,
                    "total_amount": products_data["total_amount"],
                    "otp": otp,
                    "username": user.username,
                    "status": "paid",
                    "track_id": generate_suborder_track_id(),
                }
                suborder = await SubOrder.create(suborder_data, db)

                for product in products_data["products"]:
                    order_item_data = {
                        "product_id": product["id"],
                        "suborder_id": suborder.id,
                        "quantity": product["quantity"],
                        "product_snapshot": {
                            "name": product["name"],
                            "store_id": product["store_id"],
                            "category": product["category"],
                            "images": product["images"],
                        },
                        "unit_price": product["amount"],
                        "line_price": float(product["amount"]) * product["quantity"],
                    }
                    await OrderItem.create(order_item_data, db)

                    await dispatch_event(
                        EventNames.PRODUCT_STOCK_UPDATE,
                        ProductStockUpdateEvent(
                            product_id=product["id"], quantity=product["quantity"]
                        ),
                        db=db,
                        redis=redis,
                    )

                await dispatch_event(
                    EventNames.RESERVATION_RELEASE,
                    ReservationReleaseEvent(
                        products=products_data["products"], user_id=str(user.id)
                    ),
                    db=db,
                    redis=redis,
                )

                await dispatch_event(
                    EventNames.STORE_WALLET_CREDIT,
                    StoreWalletCreditEvent(
                        store_id=str(store.id), amount=float(products_data["total_amount"])
                    ),
                    db=db,
                    redis=redis,
                )

                await dispatch_event(
                    EventNames.EMAIL_NOTIFICATION,
                    EmailNotificationEvent(
                        email_to=store.email,
                        subject="New Order",
                        context={
                            "vendor_name": store.name,
                            "username": user.username,
                            "track_id": str(suborder.track_id),
                            "order_link": "#",
                            "year": year,
                        },
                        template_name="vendor_alert_order.html",
                    ),
                    db=db,
                    redis=redis,
                )

                await dispatch_event(
                    EventNames.PUSH_NOTIFICATION,
                    PushNotificationEvent(
                        user_id=str(store.user_id),
                        title="New Order",
                        body="A new order has been placed and is awaiting your action.",
                        data={"track_id": str(suborder.track_id), "order_id": str(order.id)},
                    ),
                    db=db,
                    redis=redis,
                )

            await dispatch_event(
                EventNames.MOBILE_EVENT,
                MobileEvent(
                    event_name="payment.processing.order_created",
                    payload={
                        "reference": reference,
                        "order_id": str(order.id),
                        "progress": 75,
                    },
                ),
                db=db,
                redis=redis,
            )

            await order.update(db, {"status": "paid"})
            await Payment.update_by_id(str(order.payment_id), {"status": "successful"}, db)

            await dispatch_event(
                EventNames.MOBILE_EVENT,
                MobileEvent(
                    event_name="payment.success",
                    payload={
                        "reference": reference,
                        "order_id": str(order.id),
                        "progress": 100,
                    },
                ),
                db=db,
                redis=redis,
            )

            await dispatch_event(
                EventNames.USER_CART_CLEAR,
                UserCartClearEvent(user_id=str(user.id)),
                db=db,
                redis=redis,
            )

            await dispatch_event(
                EventNames.EMAIL_NOTIFICATION,
                EmailNotificationEvent(
                    email_to=user.email,
                    subject="Order Received",
                    context={
                        "customer_name": user.username,
                        "year": year,
                        "track_id": str(order.track_id),
                        "order_date": now.isoformat(),
                        "currency": "NGN",
                        "total_amount": order.total_amount,
                        "order_link": "#",
                    },
                    template_name="buyer_order_confirmation.html",
                ),
                db=db,
                redis=redis,
            )

            await dispatch_event(
                EventNames.PUSH_NOTIFICATION,
                PushNotificationEvent(
                    user_id=str(user.id),
                    title="Order Received",
                    body="Your payment was successful and your order is now confirmed.",
                    data={"track_id": str(order.track_id), "order_id": str(order.id)},
                ),
                db=db,
                redis=redis,
            )

            await dispatch_event(
                EventNames.MOBILE_EVENT,
                MobileEvent(
                    event_name="payment.processing.notifications_sent",
                    payload={
                        "reference": reference,
                        "order_id": str(order.id),
                        "progress": 90,
                    },
                ),
                db=db,
                redis=redis,
            )
    finally:
        await redis.delete(lock_key)
        await redis.delete(queue_key)


async def _push_to_dlq(event: PaidOrderEvent, error_message: str) -> None:
    redis = await get_redis_client()
    dlq_message = {
        "event": event.model_dump(mode="json"),
        "error": error_message,
        "failed_at": datetime.now(UTC).isoformat(),
    }
    await redis.rpush("dlq:order_processor", json.dumps(dlq_message))


@celery_app.task(
    bind=True,
    name="app.worker.tasks.order_processor.process_paid_order",
    max_retries=5,
    default_retry_delay=10,
)
def process_paid_order(self, event_payload: dict) -> None:
    event = PaidOrderEvent.model_validate(event_payload)

    try:
        asyncio.run(_process_paid_order(event=event))
    except Exception as exc:
        retries = self.request.retries or 0
        if retries >= self.max_retries:
            asyncio.run(_push_to_dlq(event, str(exc)))
            raise

        delay_seconds = min(2 ** (retries + 1), 300)
        raise self.retry(exc=exc, countdown=delay_seconds) from exc
