from __future__ import annotations

from typing import TYPE_CHECKING, Self
from uuid import UUID as UUID_Type

from sqlalchemy import Float, ForeignKey, select, DateTime, Enum, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship

from datetime import datetime, timezone


from app.models import BaseModel
from app.models import OrderItem

if TYPE_CHECKING:
    from app.models import Store, WalletTransaction, User


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


class UserWallet(BaseModel):
    __tablename__ = "user_wallets"
    
    user_id: Mapped[UUID_Type] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    balance: Mapped[float] = mapped_column(Float, default=0.0)
    pending_balance: Mapped[float] = mapped_column(Float, default=0.0)

    user: Mapped[User] = relationship(back_populates="user_wallet", uselist=False)
    refunds: Mapped[list[Refund]] = relationship(back_populates="wallet", lazy="selectin")


class Refund(BaseModel):
    __tablename__ = "refunds"
    
    wallet_id = Mapped[UUID_Type] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user_wallets.id", ondelete="CASCADE"), nullable=False)
    order_item_id: Mapped[UUID_Type] = mapped_column(
        UUID(as_uuid=True), ForeignKey("order_items.id", ondelete="SET NULL"), nullable=False
    )
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(Enum("pending", "released", "failed", name="refund_status"), default="pending", nullable=False)
    release_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    wallet = Mapped[UserWallet] = relationship(back_populates="refunds", uselist=False)
    order_item = Mapped[OrderItem] = relationship(back_populates="refunds", uselist=False)
    
    
    async def release_refund(db: AsyncSession, wallet_id: str):
        
        now = datetime.now(timezone.utc)
        
        stmt = select(func.coalesce(func.sum(func.case(
            (Refund.release_at <= now, Refund.amount), else_=0.0
        )),0.0,).label("release_amount"),
                      func.coalesce(func.sum(func.case((Refund.release_at > now, Refund.amount), else_=0.0)), 0.0,).label("pending_amount")).where(Refund.wallet_id == wallet_id,
                                                                                                                                                    Refund.status == "pending"),

        release_amount, pending_amount = (await db.execute(stmt)).one()                                                                                                                                            

        if release_amount == 0:
            return release_amount, pending_amount
        
        stmt = select(Refund).where(Refund.wallet_id == wallet_id,
                                   Refund.status == "pending",
                                   Refund.release_at <= now)
        
        refunds_to_release = (await db.execute(stmt)).scalars().all()
        for refund in refunds_to_release:
            refund.status = "released"
            
        wallet = await db.get(UserWallet, wallet_id)
        wallet.balance += release_amount
        wallet.pending_balance = pending_amount
        
        await db.commit()
        
        return release_amount, pending_amount