from sqlalchemy import Column, String, Enum, UUID, ForeignKey
from sqlalchemy.orm import relationship
from app.models import BaseModel


class Verification(BaseModel):
    __tablename__ = "verifications"

    type = Column(String, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    id_number = Column(String, nullable=False)
    picture = Column(String, nullable=True)
    status = Column(Enum("pending", "approved", "rejected"), nullable=False, default="pending")

    user = relationship("User", back_populates="verification")