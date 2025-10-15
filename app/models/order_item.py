from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.models.basemodel import BaseModel


class OrderItem(BaseModel):
    __tablename__ = "order_items"

    product_id = Column(String, nullable=False)  # Mongodb id
    suborder_id = Column(
        UUID(as_uuid=True),
        ForeignKey("suborders.id", ondelete="CASCADE"),
        nullable=False,
    )
    quantity = Column(Integer, nullable=False)
    product_snapshot = Column(JSONB, default=dict, nullable=False)
    unit_price = Column(Integer, default=0, nullable=False)
    line_price = Column(Integer, default=0, nullable=False)

    suborder = relationship(
        "SubOrder",
        back_populates="order_items",
        uselist=False
    )
