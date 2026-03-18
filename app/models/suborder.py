from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID as UUID_Type

from sqlalchemy import Enum, ForeignKey, Integer, String, distinct, func, select
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import BaseModel

if TYPE_CHECKING:
    from app.models import Order, OrderItem, Store


class SubOrder(BaseModel):
    __tablename__ = "suborders"

    order_id: Mapped[UUID_Type] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    store_id: Mapped[UUID_Type] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False
    )
    total_amount: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    shipping_fee: Mapped[int] = mapped_column(Integer, default=0)

    status: Mapped[str] = mapped_column(
        Enum(
            "pending",
            "paid",
            "accepted",
            "declined",
            "shipped",
            "delivered",
            "cancelled",
            name="suborder_status_enum",
        ),
        default="pending",
        nullable=False,
    )
    otp: Mapped[str | None] = mapped_column(String, nullable=True)
    username: Mapped[str] = mapped_column(String, nullable=False)
    track_id: Mapped[str] = mapped_column(String, nullable=False, unique=True)

    order: Mapped[Order] = relationship(back_populates="suborders", uselist=False)

    store: Mapped[Store] = relationship(back_populates="suborders", uselist=False)

    order_items: Mapped[list[OrderItem]] = relationship(
        back_populates="suborder",
        cascade="all, delete-orphan",
        single_parent=True,
        lazy="selectin",
    )

    @classmethod
    async def get_top_products_paginated(
        cls, store_id: str, page: int, page_size: int, db: AsyncSession
    ):

        offset = (page - 1) * page_size

        total_query = await db.execute(
            select(func.count())
            .select_from(cls)
            .where(cls.store_id == store_id, cls.status == "delivered")
        )
        total_items = total_query.scalar() or 0

        result = await db.execute(
            select(cls)
            .where(cls.store_id == store_id, cls.status == "delivered")
            .order_by(cls.created_at.desc())
            .limit(page_size)
            .offset(offset)
        )
        suborders = result.scalars().all()

        items_list = []
        for sub in suborders:
            items_list.append(
                {
                    **sub.to_dict(),
                    "products": [item.to_dict() for item in sub.order_items],
                }
            )

        total_pages = (total_items + page_size - 1) // page_size

        return {
            "page": page,
            "page_size": page_size,
            "total_items": total_items,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_previous": page > 1,
            "items": items_list,
        }

    @staticmethod
    async def aggregate_suborders(
        db: AsyncSession,
        store_id: str,
        start_date,
        end_date,
    ) -> dict[str, Any]:

        stmt = select(
            func.count(SubOrder.id).label("total_orders"),
            func.count(distinct(SubOrder.username)).label("total_customers"),
            func.sum(SubOrder.total_amount).label("total_revenue"),
        ).where(
            SubOrder.store_id == store_id,
            SubOrder.status == "delivered",
            SubOrder.created_at >= start_date,
            SubOrder.created_at < end_date,
        )

        row = (await db.execute(stmt)).one_or_none()
        total_orders = int((row.total_orders if row else 0) or 0)
        total_revenue = float((row.total_revenue if row else 0.0) or 0.0)
        total_customers = int((row.total_customers if row else 0) or 0)

        aov = float(total_revenue / total_orders) if total_orders else 0.0

        return {
            "total_orders": total_orders,
            "total_revenue": total_revenue,
            "total_customers": total_customers,
            "aov": aov,
        }
