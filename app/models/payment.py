from sqlalchemy import Column, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.basemodel import BaseModel


class Payment(BaseModel):
    __tablename__ = "payments"

    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    amount = Column(Integer, nullable=False)
    currency = Column(String, default="NGN", nullable=False)
    provider = Column(String, server_default="paystack", nullable=False)
    provider_payment_id = Column(String, nullable=False)
    status = Column(
        Enum(
            "successful",
            "cancelled",
            "pending",
            "declined",
            "refunded",
            name="payment_status_enum",
        ),
        default="pending",
    )

    user = relationship(
        "User", back_populates="payments", cascade="all, delete-orphan", uselist=False
    )

    order = relationship(
        "Order", back_populates="payments", cascade="all, delete-orphan", uselist=False
    )
