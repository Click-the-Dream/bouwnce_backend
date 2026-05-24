from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID as UUID_Type

from sqlalchemy import UUID, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import BaseModel

if TYPE_CHECKING:
    from app.models import Store


class ShipmentInfo(BaseModel):
    __tablename__ = "shipment_info"

    shipping_address: Mapped[str] = mapped_column(String, nullable=False)
    store_id: Mapped[UUID_Type] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False
    )
    delivery_method: Mapped[str] = mapped_column(String, nullable=False)
    delivery_fee: Mapped[float] = mapped_column(Float, nullable=False)
    delivery_time: Mapped[str] = mapped_column(String, nullable=False)

    store: Mapped[Store] = relationship(back_populates="shipment_info", uselist=False)
