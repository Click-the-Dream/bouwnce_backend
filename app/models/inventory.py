from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models import BaseModel


class Inventory(BaseModel):
    __tablename__ = "inventories"

    product_id: Mapped[str] = mapped_column(String, nullable=False)  # Mongodb id
    available: Mapped[int] = mapped_column(Integer, nullable=False)
    reserved: Mapped[int] = mapped_column(Integer, nullable=False)
