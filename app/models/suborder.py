from sqlalchemy import Column, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

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
    shipping_fee = Column(Integer, default=0, nullable=False)
    status = Column(
        Enum(
            "pending",
            "processing",
            "shipped",
            "delivered",
            "cancelled",
            name="suborder_status_enum",
        ),
        default="pending",
        nullable=False,
    )
    otp = Column(String)

    order = relationship(
        "Order", back_populates="suborders", uselist=False
    )

    store = relationship(
        "Store", back_populates="suborders", uselist=False
    )

    order_items = relationship(
        "OrderItem", back_populates="suborder", cascade="all, delete-orphan", single_parent=True
    )
