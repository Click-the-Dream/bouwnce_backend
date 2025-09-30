from sqlalchemy import UUID, Column, ForeignKey, String
from sqlalchemy.orm import relationship

from app.models import BaseModel


class ShipmentInfo(BaseModel):
    __tablename__ = "shipment_info"

    shipping_address = Column(String, nullable=False)
    store_id = Column(
        UUID(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False
    )
    delivery_method = Column(String, nullable=False)
    delivery_fee = Column(String, nullable=False)
    delivery_time = Column(String, nullable=False)

    store = relationship("Store", back_populates="shipment_info")
