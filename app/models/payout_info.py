from sqlalchemy import Column, String, UUID, ForeignKey
from sqlalchemy.orm import relationship
from app.models import BaseModel


class PayoutInfo(BaseModel):
    __tablename__ = "payouts_info"

    account_name = Column(String, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    bank_name = Column(String, nullable=False)
    account_number = Column(String, nullable=False)
  
    user = relationship("User", back_populates="payout")