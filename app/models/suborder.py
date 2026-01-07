from typing import Any

from sqlalchemy import Column, Enum, ForeignKey, Integer, String,  func, select, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import relationship
from sqlalchemy import UniqueConstraint

from app.models.basemodel import BaseModel


class SubOrder(BaseModel):
    __tablename__ = "suborders"

    order_id = Column(
        UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    store_id = Column(
        UUID(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False
    )
    total_amount = Column(Integer, default=0, nullable=False)
    shipping_fee = Column(Integer, default=0)

    otp = Column(String)
    username = Column(String)

    status = Column(
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
    otp = Column(String)
    username = Column(String, nullable=False)

    order = relationship("Order", back_populates="suborders", uselist=False)

    store = relationship("Store", back_populates="suborders", uselist=False)

    order_items = relationship(
        "OrderItem",
        back_populates="suborder",
        cascade="all, delete-orphan",
        single_parent=True,
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

    
class SubOrderSnapshot(BaseModel):
    __tablename__ = "suborder_snapshots"
    
    store_id = Column(UUID(as_uuid=True), nullable=False)
    snapshot_time = Column(DateTime(timezone=True), nullable=False, unique=True, index=True)
    total_orders = Column(Integer, default=0, nullable=False)
    total_revenue = Column(Integer, default=0, nullable=False)
    total_customers = Column(Integer, default=0, nullable=False)
    
    __table_args__ = (
        UniqueConstraint("store_id", "snapshot_time", name="uix_store_snapshot_time"),
    )


    @staticmethod
    async def aggregate_suborders(
        db: AsyncSession,
        store_id: str,
        start_date,
        end_date,
    ) -> dict[str, Any]:

        stmt = select(
            func.coalesce(func.sum(SubOrderSnapshot.total_orders), 0).label("total_orders"),
            func.coalesce(func.sum(SubOrderSnapshot.total_revenue), 0.0).label("total_revenue"),
            func.coalesce(func.sum(SubOrderSnapshot.total_customers), 0).label("total_customers"),
        ).where(
            SubOrderSnapshot.store_id == store_id,
            SubOrderSnapshot.snapshot_time >= start_date,
            SubOrderSnapshot.snapshot_time < end_date,
        )

        row = (await db.execute(stmt)).one()
        total_orders = int(row.total_orders)
        total_revenue = float(row.total_revenue)
        total_customers = int(row.total_customers)
        aov = float(total_revenue / total_orders) if total_orders > 0 else 0.0

        return {
            "total_orders": total_orders,
            "total_revenue": total_revenue,
            "total_customers": total_customers,
            "aov": aov,
        }
