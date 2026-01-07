from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID as UUID_Type

from sqlalchemy import Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import BaseModel

if TYPE_CHECKING:
    from app.models import Order, User


class Payment(BaseModel):
    __tablename__ = "payments"

    user_id: Mapped[UUID_Type] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String, default="NGN", nullable=False)
    provider: Mapped[str] = mapped_column(
        String, server_default="paystack", nullable=False
    )
    provider_payment_id: Mapped[str] = mapped_column(String, nullable=False)
    payment_url: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(
        Enum(
            "successful",
            "cancelled",
            "initiated",
            "declined",
            "refunded",
            "abandoned",
            "failed",
            name="payment_status_enum",
        ),
        default="initiated",
    )

    user: Mapped[User] = relationship(back_populates="payments", uselist=False)

    order: Mapped[Order] = relationship(back_populates="payment", uselist=False)
