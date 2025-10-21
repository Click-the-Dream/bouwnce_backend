from sqlalchemy import Integer, Float, Column, ForeignKey, Enum
from sqlalchemy.orm import relationship
from app.models.basemodel import BaseModel


class WalletTransaction(BaseModel):
    __tablename__ = "wallet_transactions"
    
    wallet_id = Column(Integer, ForeignKey("wallets.id", ondelete="CASCADE"), nullable=False)
    amount = Column(Float, nullable=False)
    transaction_type = Column(
        Enum("deposit", "withdrawal", "transfer", name="transaction_type_enum"),
        nullable=False,
    )
    status = Column(
        Enum("pending", "completed", "failed", name="transaction_status_enum"),
        nullable=False,
        default="pending",
    )
    
    wallet = relationship("Wallet", back_populates="transactions")
