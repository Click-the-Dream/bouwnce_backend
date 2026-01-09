from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID as UUID_Type

from sqlalchemy import Enum, ForeignKey, Integer, String, select
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import BaseModel

if TYPE_CHECKING:
    from app.models import SubOrder


class OrderItem(BaseModel):
    __tablename__ = "order_items"

    product_id: Mapped[str] = mapped_column(String, nullable=False)  # Mongodb id
    suborder_id: Mapped[UUID_Type] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("suborders.id", ondelete="CASCADE"),
        nullable=False,
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    product_snapshot: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    unit_price: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    line_price: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(
        Enum("pending", "accepted", "declined", name="order_item_status_enum"),
        default="pending",
        nullable=False,
    )

    suborder: Mapped[SubOrder] = relationship(
        back_populates="order_items", uselist=False
    )

    @classmethod
    async def get_by_suborder_ids(cls, db: AsyncSession, suborder_ids: list[str]):
        result = await db.execute(select(cls).where(cls.suborder_id.in_(suborder_ids)))

        return result.scalars().all()
