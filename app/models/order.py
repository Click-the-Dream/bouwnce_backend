from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self
from uuid import UUID as UUID_Type

from pydantic import BaseModel as PydnaticBaseModel
from redis.asyncio import Redis
from sqlalchemy import Enum, Float, ForeignKey, String, func, select
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship, selectinload

from app.models import BaseModel
from app.models.products import product_domain

if TYPE_CHECKING:
    from app.models import Cart, Payment, SubOrder, User


class ProductMetadata(PydnaticBaseModel):
    id: str
    store_id: str
    name: str
    category: str
    images: list[dict[str, str]]
    stock: int
    quantity: int
    amount: int
    error: str | None = None


class Order(BaseModel):
    __tablename__ = "orders"

    user_id: Mapped[UUID_Type] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    payment_id: Mapped[UUID_Type] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("payments.id", ondelete="CASCADE"),
        nullable=False,
    )
    total_amount: Mapped[float] = mapped_column(Float, nullable=False)

    products: Mapped[list[dict]] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )

    idempotent_key: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    reference_token: Mapped[str] = mapped_column(String, nullable=False, unique=True)

    status: Mapped[str] = mapped_column(
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

    track_id: Mapped[str] = mapped_column(String, nullable=False, unique=True)

    username: Mapped[str] = mapped_column(String, nullable=False)

    user: Mapped[User] = relationship(back_populates="orders", uselist=False)

    payment: Mapped[Payment] = relationship(
        back_populates="order", uselist=False, lazy="joined"
    )

    suborders: Mapped[list[SubOrder]] = relationship(
        back_populates="order", cascade="all, delete-orphan", lazy="selectin"
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
    ) -> tuple[list[ProductMetadata], list[ProductMetadata]]:
        """Check through user cart, returns list of available and out of stock products

        returns: (available_products, unavailable_products)
        """
        product_ids = [str(cart.product_id) for cart in carts]
        products = await product_domain.get_products_by_ids(product_ids)

        product_list = await product_domain.serialize_products(products, redis)
        product_list = product_list
        available_products = []
        unavailable_products = []

        product_list_dicts = {}
        for product in product_list:
            product_list_dicts[product["id"]] = product

        for cart in carts:
            product = product_list_dicts[str(cart.product_id)]

            product_model = ProductMetadata(
                id=product["id"],
                store_id=product["store_id"],
                name=product["name"],
                category=product["category"],
                images=product["images"],
                stock=product["stock"],
                quantity=cart.quantity,
                amount=product["amount"],
            )

            if (
                product["stock"] - cart.quantity >= 0
            ):  # The stock field as been converted to avaialable stock
                available_products.append(product_model)
            else:
                product_model.error = "Product stock not enough"
                unavailable_products.append(product_model)

        return available_products, unavailable_products

    @staticmethod
    async def reserve_products(
        products: list[ProductMetadata], user_id: str, redis: Redis
    ) -> tuple[list[ProductMetadata], list[ProductMetadata]]:
        """Reserve all the products in the product_dicts, and any product it can't add, it mark them as unavailable

        returns: (reserved_products, unavailable_products)
        """

        unavailable_products = []
        reserved_products = []

        for product in products:
            try:
                is_reserved, err = await product_domain.reserve_product(
                    product_id=product.id,
                    user_id=user_id,
                    quantity=product.quantity,
                    available_quantity=product.stock,
                    redis=redis,
                )

                if not is_reserved:
                    product.error = err
                    unavailable_products.append(product)
                else:
                    reserved_products.append(product)

            except Exception as e:
                print("Error occured reserving product: ", str(e))
                product.error = "Error occured while reserving product"
                unavailable_products.append(product)

        return reserved_products, unavailable_products

    @staticmethod
    def compute_total_amount(products: list[ProductMetadata]) -> float:
        total_amount = 0

        for prod in products:
            amount = float(prod.amount)
            quantity = float(prod.quantity)

            price = amount * quantity

            total_amount += price

        return total_amount

    @staticmethod
    async def release_reserved_products(
        products: list[ProductMetadata], user_id: str, redis: Redis
    ) -> bool:

        for prod in products:
            if isinstance(prod, dict):
                prod = ProductMetadata(**prod)
            await product_domain.release_product(prod.id, user_id, redis)

        return True

    @staticmethod
    def group_products_by_store(
        products: list[ProductMetadata] | list[dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:

        grouped_products = {}

        for product in products:
            if isinstance(product, dict):
                product = ProductMetadata(**product)
            store_id = product.store_id

            # add the store to grouped_product if not present
            if store_id not in grouped_products:
                grouped_products[store_id] = {"products": [], "total_amount": 0}

            # Then add the product to the store key and compute the total amount
            grouped_products[store_id]["products"].append(product.model_dump())

            amount = float(product.quantity) * product.amount
            grouped_products[store_id]["total_amount"] += amount

        return grouped_products

    @classmethod
    async def fetch_owner_of_order(cls, user_id: str, db: AsyncSession) -> User | None:
        result = await db.execute(select(User).where(User.id == user_id))

        return result.scalar_one_or_none()

    @classmethod
    async def fetch_user_orders(
        cls, user_id: str, db: AsyncSession, page: int = 1, page_size: int = 10
    ) -> dict[str, Any]:

        page = max(1, page)
        page_size = max(1, page_size)
        offset = (page - 1) * page_size

        smt = (
            select(cls)
            .where(cls.user_id == user_id)
            .options(selectinload(Order.suborders).selectinload(SubOrder.order_items))
            .offset(offset)
            .limit(page_size)
        )

        count_query = (
            select(func.count()).select_from(cls).where(cls.user_id == user_id)
        )
        count_result = await db.execute(count_query)
        total_count = count_result.scalar() or 0

        result = await db.execute(smt)
        orders = result.scalars().all()

        return {
            "orders": orders,
            "page": page,
            "page_size": page_size,
            "total": total_count,
        }

    @classmethod
    async def fetch_user_order_by_id(
        cls,
        id: str,
        db: AsyncSession,
    ) -> Self | None:

        smt = (
            select(cls)
            .where(cls.id == id)
            .options(selectinload(cls.suborders).selectinload(SubOrder.order_items))
        )
        result = await db.execute(smt)
        return result.scalar_one_or_none()

    @classmethod
    async def fetch_user_order_by_track_id(
        cls, track_id: str, db: AsyncSession
    ) -> Self | None:

        smt = (
            select(cls)
            .where(cls.track_id == track_id)
            .options(selectinload(cls.suborders).selectinload(SubOrder.order_items))
        )

        result = await db.execute(smt)
        return result.scalar_one_or_none()
