from sqlalchemy import Column, DateTime, UUID, Boolean
from uuid import uuid4

class BaseModel:
    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid4)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    deleted_at = Column(DateTime, nullable=True)
    is_deleted = Column(Boolean, default=False, nullable=False)