import asyncio
from time import time

from redis import Redis
from redis.exceptions import WatchError

from app.core.config import settings


class OrderDomain:
    def __init__(self):
        self._max_tries = 10

    def _compute_reserved_product_key(self, product_id: str) -> str:
        """Return a redis key used to store reserved product stock"""
        return f"reserved:product:{product_id}"

    def _compute_reserved_product_user_key(self, product_id: str, user_id: str) -> str:
        """Return a redis key used to store reserved product stock of a user"""
        return f"reserved:product:{product_id}:{user_id}"

    async def get_avaiable_product_stock(
        self, product_id: str, current_avaialability: int, redis: Redis
    ) -> int:
        """Check if a product is still available by checking against reserve stock"""

        if current_avaialability <= 0:
            return 0

        redis_key = self._compute_reserved_product_key(product_id)
        reserved_stock = await redis.get(redis_key)
        if not reserved_stock:
            return current_avaialability

        return current_avaialability - int(reserved_stock)

    async def reserve_product(
        self,
        product_id: str,
        user_id: str,
        quantity: int,
        available_quantity: int,
        redis: Redis,
    ) -> bool:
        """Reserve stock by adding to temporarily adding to redis"""
        product_key = self._compute_reserved_product_key(product_id)
        product_user_key = self._compute_reserved_product_user_key(product_id, user_id)

        async with redis.pipeline() as pipe:
            for attempt in range(self._max_tries):
                try:
                    await pipe.watch(product_key)

                    currently_reserved_prod = int(await pipe.get(product_key) or 0)

                    if currently_reserved_prod + quantity > available_quantity:
                        await pipe.unwatch()
                        return False, "Not enough available quantity"

                    # Multiple Execution for atomic transaction
                    now = time() + int(settings.RESERVATION_TTL)

                    pipe.multi()
                    pipe.incrby(product_key, quantity)
                    pipe.set(product_user_key, quantity)
                    pipe.ZADD("reservation_expiries", {product_user_key: now})
                    await pipe.execute()

                    return True
                except WatchError:

                    # Retry if race condition occured
                    if attempt < self._max_tries - 1:
                        await asyncio.sleep(0.05)
                        continue
                    else:
                        return False
                except Exception as e:

                    await pipe.unwatch()
                    raise e

    def check_cart_availability():
        """Check through user cart, returns list of available and out of stock products"""
        pass
