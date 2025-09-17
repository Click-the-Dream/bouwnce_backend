from sqlalchemy import Column, String, UUID, ForeignKey
from sqlalchemy.orm import relationship
from app.models import BaseModel

class StoreInfo(BaseModel):
    __tablename__ = "store_info"

    store_logo = Column(String, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    store_banner = Column(String, nullable=True)
    store_description = Column(String, nullable=False)
    
    user = relationship("User", back_populates="store_info")
