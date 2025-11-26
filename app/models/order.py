from typing import Any, Self

from redis.asyncio import Redis
from sqlalchemy import Column, Enum, ForeignKey, Integer, String, select
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import relationship

from app.models.basemodel import BaseModel
from app.models.cart import Cart
from app.models.products import product_domain


class Order(BaseModel):
    __tablename__ = "orders"

    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    payment_id = Column(
        UUID(as_uuid=True),
        ForeignKey("payments.id", ondelete="CASCADE"),
        nullable=False,
    )
    total_amount = Column(Integer, nullable=False)

    products = Column(JSONB, nullable=False, default=list)

    idempotent_key = Column(String, nullable=False, unique=True)
    reference_token = Column(String, nullable=False, unique=True)

    status = Column(
        Enum(
            "initiated",
            "failed",
            "cancelled",
            "declined",
            "paid",
            "abandoned",
            "accepted",
            "out_for_delivery",
            "delivered",
            name="order_status_enum",
        ),
        default="initiated",
    )

    user = relationship("User", back_populates="orders", uselist=False)

    payments = relationship(
        "Payment",
        back_populates="order",
        cascade="all, delete-orphan",
        single_parent=True,
    )

    suborders = relationship(
        "SubOrder", back_populates="order", cascade="all, delete-orphan"
    )

    @classmethod
    async def get_by_idempotent_key(
        cls, idempotent_key: str, db: AsyncSession
    ) -> Self | None:
        result = await db.execute(
            select(cls).where(cls.idempotent_key == idempotent_key)
        )
        order = result.scalar_one_or_none()

        return order

    @classmethod
    async def get_by_reference(cls, reference: str, db: AsyncSession) -> Self | None:
        result = await db.execute(select(cls).where(cls.reference_token == reference))
        order = result.scalar_one_or_none()

        return order

    @staticmethod
    async def check_cart_availability(
        carts: list[Cart], redis: Redis
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Check through user cart, returns list of available and out of stock products

        returns: (available_products, unavailable_products)
        """
        product_ids = [str(cart.product_id) for cart in carts]
        products = await product_domain.get_products_by_ids(product_ids)

        product_list = await product_domain.serialize_products(products, redis)

        available_products = []
        unavailable_products = []

        for cart, product in zip(carts, product_list, strict=False):
            if (
                product["stock"] - cart.quantity >= 0
            ):  # The stock field as been converted to avaialable stock
                product["quantity"] = cart.quantity
                available_products.append(product)
            else:
                product["error"] = "Product stock not enough"
                unavailable_products.append(product)

        return available_products, unavailable_products

    @staticmethod
    async def reserve_products(
        product_dicts: list[dict[str, Any]], user_id: str, redis: Redis
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Reserve all the products in the product_dicts, and any product it can't add, it mark them as unavailable

        returns: (reserved_products, unavailable_products)
        """

        unavailable_products = []
        reserved_products = []

        for product in product_dicts:
            try:
                is_reserved, err = await product_domain.reserve_product(
                    product_id=product["id"],
                    user_id=user_id,
                    quantity=product["quantity"],
                    available_quantity=product["stock"],
                    redis=redis,
                )

                if not is_reserved:
                    product["error"] = err
                    unavailable_products.append(product)
                else:
                    reserved_products.append(product)

            except Exception as e:
                print("Error occured reserving product: ", str(e))
                product["error"] = "Error occured while reserving product"
                unavailable_products.append(product)

        return reserved_products, unavailable_products

    @staticmethod
    async def compute_total_amount(products: list[dict[str, Any]]) -> float:
        total_amount = 0

        for prod in products:
            amount = float(prod["amount"])
            quantity = float(prod["quantity"])

            price = amount * quantity

            total_amount += price

        return total_amount

    @staticmethod
    async def release_reserved_products(
        products: list[dict[str, Any]], user_id: str, redis: Redis
    ) -> bool:

        for prod in products:
            await product_domain.release_product(prod["id"], user_id, redis)

        return True

    @staticmethod
    def group_products_by_store(
        products: list[dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:

        grouped_products = {}

        for product in products:
            store_id = product["store_id"]

            # add the store to grouped_product if not present
            if store_id not in grouped_products:
                grouped_products[store_id] = {"products": [], "total_amount": 0}

            # Then add the product to the store key and compute the total amount
            grouped_products[store_id]["products"].append(product.copy())

            amount = product["quantity"] * product["amount"]
            grouped_products[store_id]["total_amount"] += amount

        return grouped_products
