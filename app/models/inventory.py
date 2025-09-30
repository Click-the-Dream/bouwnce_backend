from sqlalchemy import Column, Integer, String

from app.models.basemodel import BaseModel


class Inventory(BaseModel):
    __tablename__ = "inventories"

    product_id = Column(String, nullable=False)  # Mongodb id
    available = Column(Integer, nullable=False)
    reserved = Column(Integer, nullable=False)
