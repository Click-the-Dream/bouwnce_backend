from typing import Self

from sqlalchemy import Column, ForeignKey, String, select
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

    user = relationship("User", back_populates="stores", uselist=False)

    buisiness_info = relationship("BusinessInfo", back_populates="store", uselist=False, cascade="all, delete-orphan")
    contact_info = relationship("ContactInfo", back_populates="store", uselist=False, cascade="all, delete-orphan")
    store_info = relationship("StoreInfo", back_populates="store", uselist=False, cascade="all, delete-orphan")
    payout_info = relationship("PayoutInfo", back_populates="store", uselist=False, cascade="all, delete-orphan")
    shipment_info = relationship("ShipmentInfo", back_populates="store", uselist=False, cascade="all, delete-orphan")

    suborders = relationship("SubOrder", back_populates="store", cascade="all, delete-orphan")
    
    @classmethod
    async def get_by_user_id(cls, id: str, db: AsyncSession) -> Self:
        result = await db.execute(select(cls).where(cls.user_id == id))
        store = result.scalar_one_or_none()
        if not store:
            raise ValueError("User doesn't have a store")
        return store
