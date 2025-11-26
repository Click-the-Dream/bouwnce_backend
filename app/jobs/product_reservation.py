from time import time

from sqlalchemy import text, update
from sqlalchemy.sql import func

from app.db.postgres_db_conn import get_async_session
from app.db.redis import get_redis_client
from app.models.order import Order
from app.models.payment import Payment


async def product_reservation():

    now = time()

    # Fetch all reservations that have expired
    redis = await get_redis_client()
    expired_reservations = await redis.zrangebyscore(
        "reservation_expiries", min="-inf", max=now
    )

    for res_key in expired_reservations:
        print("Found expired reservation: ", res_key)

        #  Parse the reservered_key to get product_id and user_id
        res_key = res_key.decode("utf-8") if isinstance(res_key, bytes) else res_key

        _, _, product_id, user_id = res_key.split(":")

        product_key = f"reserved:product:{product_id}"

        qtty = await redis.get(res_key)

        if not qtty:
            continue  # Might already be cleaned up, so just continue

        qtty = int(qtty)

        async with redis.pipeline() as pipe:
            pipe.decrby(product_key, qtty)
            pipe.delete(res_key)
            pipe.zrem("reservation_expiries", res_key)
            await pipe.execute()


async def mark_order_and_payment_abandoned():
    async with get_async_session() as db:
        order_statement = (
            update(Order)
            .where(
                Order.status == "initiated",
                Order.created_at <= func.now() - text("INTERVAL '15 minutes'"),
            )
            .values(status="abandoned")
        )

        order_updated_result = await db.execute(order_statement)
        order_updated_count = order_updated_result.rowcount

        payment_statement = (
            update(Payment)
            .where(
                Payment.status == "initiated",
                Payment.created_at <= func.now() - text("INTERVAL '15 minutes'"),
            )
            .values(status="abandoned")
        )

        payment_updated_result = await db.execute(payment_statement)
        payment_updated_count = payment_updated_result.rowcount

        print(f"✅ Marked {order_updated_count} orders abandoned")
        print(f"✅ Marked {payment_updated_count} payment abandoned")
