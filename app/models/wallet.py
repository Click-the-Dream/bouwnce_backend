from typing import Self

from sqlalchemy import Column, Float, ForeignKey, select
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import relationship

from app.models.basemodel import BaseModel


class Wallet(BaseModel):
    __tablename__ = "wallets"

    store_id = Column(
        UUID(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False
    )

    available_balance = Column(Float, default=0.0)
    pending_balance = Column(Float, default=0.0)
    withdrawable_balance = Column(Float, default=0.0)

    store = relationship("Store", back_populates="wallets", uselist=False)
    transactions = relationship(
        "WalletTransaction",
        back_populates="wallet",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    @classmethod
    async def get_by_store_id(cls, store_id: str, db: AsyncSession) -> Self:

        result = await db.execute(select(cls).where(cls.store_id == store_id))

        wallet = result.scalar_one_or_none()

        return wallet
