from typing import Self

from sqlalchemy import JSON, Boolean, Column, ForeignKey, String, select
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import relationship

from app.models.basemodel import BaseModel


class Store(BaseModel):
    __tablename__ = "stores"

    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name = Column(String, unique=True, nullable=False)
    address = Column(String, nullable=False)
    phone_number = Column(String, nullable=False)
    email = Column(String, nullable=False)
    store_logo = Column(JSON, nullable=True)
    store_banner = Column(JSON, nullable=True)
    store_description = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    user = relationship("User", back_populates="stores", uselist=False)

    contact_info = relationship(
        "ContactInfo",
        back_populates="store",
        uselist=False,
        cascade="all, delete-orphan",
    )

    payout_info = relationship(
        "PayoutInfo",
        back_populates="store",
        uselist=False,
        cascade="all, delete-orphan",
    )
    shipment_info = relationship(
        "ShipmentInfo",
        back_populates="store",
        cascade="all, delete-orphan",
    )
    suborders = relationship(
        "SubOrder", back_populates="store", cascade="all, delete-orphan"
    )

    wallets = relationship("Wallet", back_populates="store", uselist=False)

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
