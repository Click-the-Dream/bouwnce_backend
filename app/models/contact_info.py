from sqlalchemy import Column, String, UUID, ForeignKey
from sqlalchemy.orm import relationship
from app.models import BaseModel


class ContactInfo(BaseModel):
    __tablename__ = "contact_info"

    name = Column(String, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=True)
    email = Column(String, nullable=False)
    phone_number = Column(String, nullable=False)
    
    user = relationship("User", back_populates="contact_info")