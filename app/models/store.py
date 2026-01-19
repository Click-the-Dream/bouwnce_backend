from __future__ import annotations

from typing import TYPE_CHECKING, Self
from uuid import UUID as UUID_Type

from sqlalchemy import JSON, Boolean, ForeignKey, String, select
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import BaseModel

if TYPE_CHECKING:
    from app.models import ContactInfo, PayoutInfo, ShipmentInfo, SubOrder, User, Wallet


class Store(BaseModel):
    __tablename__ = "stores"

    user_id: Mapped[UUID_Type] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    address: Mapped[str] = mapped_column(String, nullable=False)
    phone_number: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False)
    store_logo: Mapped[dict] = mapped_column(JSON, nullable=True)
    store_banner: Mapped[dict] = mapped_column(JSON, nullable=True)
    store_description: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user: Mapped[User] = relationship(back_populates="stores", uselist=False)

    contact_info: Mapped[list[ContactInfo]] = relationship(
        back_populates="store",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    payout_info: Mapped[list[PayoutInfo]] = relationship(
        back_populates="store",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    shipment_info: Mapped[list[ShipmentInfo]] = relationship(
        back_populates="store", cascade="all, delete-orphan", lazy="selectin"
    )
    suborders: Mapped[list[SubOrder]] = relationship(
        back_populates="store", cascade="all, delete-orphan", lazy="selectin"
    )

    wallets: Mapped[Wallet] = relationship(
        back_populates="store", uselist=False, lazy="joined"
    )

    @classmethod
    async def get_by_user_id(cls, id: str, db: AsyncSession) -> Self:
        result = await db.execute(select(cls).where(cls.user_id == id))
        store = result.scalar_one_or_none()
        if not store:
            raise ValueError("User doesn't have a store")
        return store

    @classmethod
    async def get_by_name(cls, name: str, db: AsyncSession) -> Self:

        result = await db.execute(select(cls).where(cls.name == name))
        store = result.scalar_one_or_none()

        return store

    @classmethod
    async def get_all(cls, db: AsyncSession) -> list:
        result = await db.execute(select(cls))
        return result.scalars().all()

    async def update_store_wallet(self, amount: int, db: AsyncSession) -> Self:
        wallet = await Wallet.get_by_store_id(str(self.id), db)

        if not wallet:
            return

        wallet.available_balance = wallet.available_balance + amount
        wallet.pending_balance = wallet.pending_balance + amount

        await wallet.save(db)

    @classmethod
    async def get_store_by_ids(
        cls, store_ids: list[str], db: AsyncSession
    ) -> list[Self]:
        stmt = select(cls).where(cls.id.in_(store_ids))

        result = await db.execute(stmt)
        stores = result.scalars().all()

        return stores
