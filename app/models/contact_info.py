from sqlalchemy import UUID, Column, ForeignKey, String
from sqlalchemy.orm import relationship

from app.models import BaseModel


class ContactInfo(BaseModel):
    __tablename__ = "contact_info"

    name = Column(String, nullable=False)
    store_id = Column(
        UUID(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False
    )
    title = Column(String, nullable=True)
    email = Column(String, nullable=False)
    phone = Column(String, nullable=False)

    store = relationship("Store", back_populates="contact_info")
