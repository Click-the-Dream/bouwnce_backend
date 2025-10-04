from sqlalchemy import UUID, Column, ForeignKey, String
from sqlalchemy.orm import relationship

from app.models import BaseModel


class BusinessInfo(BaseModel):
    __tablename__ = "business_info"

    name = Column(String, nullable=False)
    store_id = Column(
        UUID(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False
    )
    address = Column(String, nullable=False)
    phone_number = Column(String, nullable=False)
    email = Column(String, nullable=False)
    btype = Column(String, nullable=False)

    store = relationship("Store", back_populates="business_info")
