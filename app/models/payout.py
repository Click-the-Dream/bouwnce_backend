from sqlalchemy import UUID, Column, ForeignKey, String
from sqlalchemy.orm import relationship

from app.models import BaseModel


class Payout(BaseModel):
    __tablename__ = "payouts"

    account_name = Column(String, nullable=False)
    store_id = Column(
        UUID(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False
    )
    bank_name = Column(String, nullable=False)
    account_number = Column(String, nullable=False)

    store = relationship("Store", back_populates="payout")
