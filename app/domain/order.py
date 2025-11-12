from redis import Redis


class OrderDomain:
    def _compute_reserved_product_key(self, product_id: str) -> str:
        """Return a redis key used to store reserved product stock"""
        return f"reserved:{product_id}"

    def _compute_reserved_product_user_key(self, product_id: str, user_id: str) -> str:
        """Return a redis key used to store reserved product stock of a user"""
        return f"reserved:{product_id}:{user_id}"

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

    def reserve_product():
        """Reserve stock by adding to temporarily adding to redis"""
        pass

    def check_cart_availability():
        """Check through user cart, returns list of available and out of stock products"""
        pass
