import json
from dataclasses import dataclass
from typing import Any

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import MOBILE_EVENTS_STREAM_KEY, PAYMENT_PROGRESS_KEY_PREFIX
from app.models.cart import Cart
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.products import product_domain
from app.models.store import Store
from app.models.suborder import SubOrder
from app.models.wallet import UserWallet
from app.worker.tasks.email import send_email_using_worker


class EventNames:
    PRODUCT_STOCK_UPDATE = "product.stock.update"
    RESERVATION_RELEASE = "reservation.release"
    STORE_WALLET_CREDIT = "store.wallet.credit"
    USER_CART_CLEAR = "user.cart.clear"
    EMAIL_NOTIFICATION = "email.notification.send"
    PUSH_NOTIFICATION = "push.notification.send"
    ORDER_ITEM_CANCEL = "order.item.cancel"
    ORDER_ITEM_ACCEPT = "order.item.accept"
    SUBORDER_CANCEL = "suborder.cancel"
    BUYER_WALLET_CREDIT = "buyer.wallet.credit"
    STORE_WALLET_RELEASE = "store.wallet.release"
    ORDER_COMPLETE = "order.complete"
    MOBILE_EVENT = "mobile.event"


async def _publish_mobile_stream_event(
    redis: Redis, *, event_name: str, payload: dict[str, Any]
) -> None:
    # Store payload as JSON so mobile clients can consume consistently.
    await redis.xadd(
        MOBILE_EVENTS_STREAM_KEY,
        {"event_name": event_name, "payload": json.dumps(payload)},
        maxlen=5000,
        approximate=True,
    )


async def _set_payment_progress(
    redis: Redis,
    *,
    reference: str,
    progress: int,
    status: str,
    order_id: str | None = None,
) -> None:
    key = f"{PAYMENT_PROGRESS_KEY_PREFIX}{reference}"
    value = {
        "reference": reference,
        "order_id": order_id,
        "progress": int(max(-100, min(100, progress))),
        "status": status,
    }
    await redis.set(key, json.dumps(value), ex=60 * 30)


@dataclass
class ProductStockUpdateEvent:
    product_id: str
    quantity: int


@dataclass
class ReservationReleaseEvent:
    products: list[dict[str, Any]]
    user_id: str


@dataclass
class StoreWalletCreditEvent:
    store_id: str
    amount: float


@dataclass
class UserCartClearEvent:
    user_id: str


@dataclass
class EmailNotificationEvent:
    email_to: str
    subject: str
    context: dict[str, Any]
    template_name: str


@dataclass
class OrderItemCancelEvent:
    order_item_id: str


@dataclass
class PushNotificationEvent:
    user_id: str
    title: str
    body: str
    data: dict[str, Any]


@dataclass
class OrderItemAcceptEvent:
    order_item_id: str


@dataclass
class SubOrderCancelEvent:
    suborder_id: str


@dataclass
class BuyerWalletCreditEvent:
    user_id: str
    amount: float


@dataclass
class StoreWalletReleaseEvent:
    store_id: str
    amount: float


@dataclass
class OrderCompleteEvent:
    order_id: str


@dataclass
class MobileEvent:
    event_name: str
    payload: dict[str, Any]


async def dispatch_event(
    event_name: str,
    payload: Any,
    *,
    db: AsyncSession,
    redis: Redis | None,
) -> None:
    if event_name == EventNames.MOBILE_EVENT:
        if redis is None:
            raise ValueError("redis client is required for mobile event")
        # If this is a payment progress event, cache latest progress for quick reads.
        if payload.event_name.startswith("payment."):
            reference = str(payload.payload.get("reference") or "")
            progress = int(payload.payload.get("progress") or 0)
            if reference:
                await _set_payment_progress(
                    redis,
                    reference=reference,
                    progress=progress,
                    status=payload.event_name,
                    order_id=payload.payload.get("order_id"),
                )
        await _publish_mobile_stream_event(
            redis, event_name=payload.event_name, payload=payload.payload
        )
        return
    if event_name == EventNames.PRODUCT_STOCK_UPDATE:
        await product_domain.decrease_product_stock_and_increase_total_sales(
            payload.product_id, payload.quantity
        )
        return

    if event_name == EventNames.RESERVATION_RELEASE:
        if redis is None:
            raise ValueError("redis client is required for reservation release event")
        await Order.release_reserved_products(payload.products, payload.user_id, redis)
        return

    if event_name == EventNames.STORE_WALLET_CREDIT:
        store = await Store.get_by_id(payload.store_id, db)
        await store.update_store_wallet(amount=payload.amount, db=db)
        return

    if event_name == EventNames.USER_CART_CLEAR:
        await Cart.delete_by_user_id(payload.user_id, db)
        return

    if event_name == EventNames.EMAIL_NOTIFICATION:
        send_email_using_worker.delay(
            email_to=payload.email_to,
            subject=payload.subject,
            context=payload.context,
            template_name=payload.template_name,
        )
        return

    if event_name == EventNames.PUSH_NOTIFICATION:
        if redis is None:
            raise ValueError("redis client is required for push notification event")
        payload_dict = {
            "user_id": payload.user_id,
            "title": payload.title,
            "body": payload.body,
            "data": payload.data,
        }
        await redis.rpush(
            "notifications:push:queue",
            json.dumps(payload_dict),
        )
        await _publish_mobile_stream_event(
            redis, event_name=EventNames.PUSH_NOTIFICATION, payload=payload_dict
        )
        return

    if event_name == EventNames.BUYER_WALLET_CREDIT:
        user_wallet = await UserWallet.get_one(
            db=db, filter={"user_id": payload.user_id}
        )
        if not user_wallet:
            user_wallet = await UserWallet.create({"user_id": payload.user_id}, db)

        user_wallet.balance += float(payload.amount)
        await user_wallet.save(db)
        return

    if event_name == EventNames.STORE_WALLET_RELEASE:
        store = await Store.get_by_id(payload.store_id, db)
        wallet = store.wallets
        if not wallet:
            return

        amount = min(float(payload.amount), float(wallet.pending_balance or 0))
        if amount <= 0:
            return

        wallet.pending_balance -= amount
        wallet.withdrawable_balance += amount
        await wallet.save(db)
        return

    if event_name == EventNames.ORDER_ITEM_ACCEPT:
        order_item = await OrderItem.get_by_id(payload.order_item_id, db)
        if order_item.status == "accepted":
            return

        order_item.status = "accepted"
        await order_item.save(db)

        suborder = order_item.suborder
        if suborder:
            active_items = [
                item for item in suborder.order_items if item.status != "declined"
            ]
            if active_items and all(item.status == "accepted" for item in active_items):
                if suborder.status != "accepted":
                    suborder.status = "accepted"
                    await suborder.save(db)

                order = suborder.order
                if order:
                    active_suborders = [
                        so for so in order.suborders if so.status != "cancelled"
                    ]
                    if (
                        active_suborders
                        and all(so.status == "accepted" for so in active_suborders)
                        and order.status not in ["accepted", "delivered", "cancelled"]
                    ):
                        order.status = "accepted"
                        await order.save(db)

        return

    if event_name == EventNames.ORDER_ITEM_CANCEL:
        order_item = await OrderItem.get_by_id(payload.order_item_id, db)
        if order_item.status == "declined":
            return

        refund_amount = float(order_item.line_price)

        order_item.status = "declined"
        await order_item.save(db)

        suborder = order_item.suborder
        if suborder:
            await suborder.subtract_total_amount(int(order_item.line_price), db)

            store = await Store.get_by_id(str(suborder.store_id), db)
            wallet = store.wallets
            if wallet:
                debit_amount = min(
                    refund_amount,
                    float(wallet.pending_balance or 0),
                    float(wallet.available_balance or 0),
                )
                if debit_amount > 0:
                    wallet.pending_balance -= debit_amount
                    wallet.available_balance -= debit_amount
                    await wallet.save(db)

            active_items = [
                item for item in suborder.order_items if item.status != "declined"
            ]
            if len(active_items) == 0:
                suborder.status = "cancelled"
                await suborder.save(db)

            order = suborder.order
            if order:
                active_suborders = [
                    so for so in order.suborders if so.status != "cancelled"
                ]
                if len(active_suborders) == 0:
                    order.status = "cancelled"
                    await order.save(db)

                await dispatch_event(
                    EventNames.BUYER_WALLET_CREDIT,
                    BuyerWalletCreditEvent(
                        user_id=str(order.user_id), amount=refund_amount
                    ),
                    db=db,
                    redis=redis,
                )
        return

    if event_name == EventNames.SUBORDER_CANCEL:
        suborder = await SubOrder.get_by_id(payload.suborder_id, db)
        if suborder.status == "cancelled":
            return

        total_refund = 0.0
        for order_item in suborder.order_items:
            if order_item.status != "declined":
                order_item.status = "declined"
                await order_item.save(db)
                total_refund += float(order_item.line_price)

        suborder.status = "cancelled"
        await suborder.save(db)

        if total_refund > 0:
            store = await Store.get_by_id(str(suborder.store_id), db)
            wallet = store.wallets
            if wallet:
                debit_amount = min(
                    total_refund,
                    float(wallet.pending_balance or 0),
                    float(wallet.available_balance or 0),
                )
                if debit_amount > 0:
                    wallet.pending_balance -= debit_amount
                    wallet.available_balance -= debit_amount
                    await wallet.save(db)

        order = suborder.order
        if order:
            active_suborders = [
                so for so in order.suborders if so.status != "cancelled"
            ]
            if len(active_suborders) == 0:
                order.status = "cancelled"
                await order.save(db)

            if total_refund > 0:
                await dispatch_event(
                    EventNames.BUYER_WALLET_CREDIT,
                    BuyerWalletCreditEvent(
                        user_id=str(order.user_id), amount=total_refund
                    ),
                    db=db,
                    redis=redis,
                )
        return

    if event_name == EventNames.ORDER_COMPLETE:
        order = await Order.get_by_id(payload.order_id, db)
        if order.status == "delivered":
            return

        for suborder in order.suborders:
            if suborder.status == "cancelled":
                continue

            if suborder.status != "delivered":
                suborder.status = "delivered"
                await suborder.save(db)

            await dispatch_event(
                EventNames.STORE_WALLET_RELEASE,
                StoreWalletReleaseEvent(
                    store_id=str(suborder.store_id), amount=float(suborder.total_amount)
                ),
                db=db,
                redis=redis,
            )

        if order.status != "delivered":
            order.status = "delivered"
            await order.save(db)
        return

    raise ValueError(f"Unsupported event: {event_name}")
