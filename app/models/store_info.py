from sqlalchemy import UUID, Column, ForeignKey, String
from sqlalchemy.orm import relationship

from app.models import BaseModel


class StoreInfo(BaseModel):
    __tablename__ = "store_info"

    store_logo = Column(String, nullable=False)
    store_id = Column(
        UUID(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False
    )
    address = Column(String, nullable=False)
    phone_number = Column(String, nullable=False)
    email = Column(String, nullable=False)

    store = relationship("Store", back_populates="store_info")
