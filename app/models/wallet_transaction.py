from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID as UUID_Type

from sqlalchemy import Enum, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import BaseModel

if TYPE_CHECKING:
    from app.models import Wallet


class WalletTransaction(BaseModel):
    __tablename__ = "wallet_transactions"

    wallet_id: Mapped[UUID_Type] = mapped_column(
        UUID(as_uuid=True), ForeignKey("wallets.id", ondelete="CASCADE"), nullable=False
    )
    amount: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    transaction_type: Mapped[str] = mapped_column(
        Enum("deposit", "withdrawal", "transfer", name="transaction_type_enum"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        Enum("pending", "completed", "failed", name="transaction_status_enum"),
        nullable=False,
        default="pending",
    )

    wallet: Mapped[Wallet] = relationship(back_populates="transactions", uselist=False)
