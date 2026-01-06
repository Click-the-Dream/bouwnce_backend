from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID as UUID_Type

from sqlalchemy import UUID, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import BaseModel

if TYPE_CHECKING:
    from app.models import Store


class PayoutInfo(BaseModel):
    __tablename__ = "payouts_info"

    account_name: Mapped[str] = mapped_column(String, nullable=False)
    store_id: Mapped[UUID_Type] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False
    )
    bank_name: Mapped[str] = mapped_column(String, nullable=False)
    account_number: Mapped[str] = mapped_column(String, nullable=False)
    security_question: Mapped[str] = mapped_column(String, nullable=False)
    security_answer: Mapped[str] = mapped_column(String, nullable=False)
    withdrawal_pin: Mapped[str] = mapped_column(String(6), nullable=False)

    store: Mapped[Store] = relationship(back_populates="payout_info", uselist=False)
