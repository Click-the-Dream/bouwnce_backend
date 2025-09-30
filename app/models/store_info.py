from sqlalchemy import UUID, Column, ForeignKey, String
from sqlalchemy.orm import relationship

from app.models import BaseModel


class StoreInfo(BaseModel):
    __tablename__ = "store_info"

    store_logo = Column(String, nullable=False)
    store_id = Column(
        UUID(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False
    )
    store_banner = Column(String, nullable=True)
    store_description = Column(String, nullable=False)

    store = relationship("Store", back_populates="store_info")
