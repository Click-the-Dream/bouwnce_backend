from sqlalchemy import Column, Enum, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.basemodel import BaseModel


class Order(BaseModel):
    __tablename__ = "orders"

    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    payment_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    total_amount = Column(Integer, nullable=False)
    status = Column(
        Enum("pending", "failed", "cancelled", "paid", name="order_status_enum"),
        default="pending",
    )

    user = relationship(
        "User", back_populates="orders", cascade="all, delete-orphan", uselist=False
    )

    payments = relationship(
        "Payment", back_populates="order", cascade="all, delete-orphan"
    )

    suborders = relationship(
        "SubOrder", back_populates="order", cascade="all, delete-orphan"
    )
