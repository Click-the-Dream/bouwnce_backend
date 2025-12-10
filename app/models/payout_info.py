from sqlalchemy import UUID, Column, ForeignKey, String
from sqlalchemy.orm import relationship

from app.models import BaseModel


class PayoutInfo(BaseModel):
    __tablename__ = "payouts_info"

    account_name = Column(String, nullable=False)
    store_id = Column(
        UUID(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False
    )
    bank_name = Column(String, nullable=False)
    account_number = Column(String, nullable=False)
    security_question = Column(String, nullable=False)
    security_answer = Column(String, nullable=False)
    withdrawal_pin = Column(String(6), nullable=False)

    store = relationship("Store", back_populates="payout_info")
