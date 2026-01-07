from __future__ import annotations

from typing import TYPE_CHECKING, Self
from uuid import UUID as UUID_Type

from sqlalchemy import Float, ForeignKey, select
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import BaseModel

if TYPE_CHECKING:
    from app.models import Store, WalletTransaction


class Wallet(BaseModel):
    __tablename__ = "wallets"

    store_id: Mapped[UUID_Type] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False
    )

    available_balance: Mapped[float] = mapped_column(Float, default=0.0)
    pending_balance: Mapped[float] = mapped_column(Float, default=0.0)
    withdrawable_balance: Mapped[float] = mapped_column(Float, default=0.0)

    store: Mapped[Store] = relationship(back_populates="wallets", uselist=False)

    transactions: Mapped[list[WalletTransaction]] = relationship(
        back_populates="wallet",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )

    @classmethod
    async def get_by_store_id(cls, store_id: str, db: AsyncSession) -> Self:

        result = await db.execute(select(cls).where(cls.store_id == store_id))

        wallet = result.scalar_one_or_none()

        return wallet
