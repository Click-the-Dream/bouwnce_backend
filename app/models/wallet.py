from sqlalchemy import Column, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
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

    user = relationship("User", back_populates="wallet")
    transactions = relationship(
        "WalletTransaction",
        back_populates="wallet",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
