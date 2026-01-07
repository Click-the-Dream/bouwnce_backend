from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID as UUID_Type

from sqlalchemy import UUID, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import BaseModel

if TYPE_CHECKING:
    from app.models import Store


class ContactInfo(BaseModel):
    __tablename__ = "contact_info"

    name: Mapped[str] = mapped_column(String, nullable=False)
    store_id: Mapped[UUID_Type] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    email: Mapped[str] = mapped_column(String, nullable=False)
    phone_number: Mapped[str] = mapped_column(String, nullable=False)

    store: Mapped[Store] = relationship(back_populates="contact_info", uselist=False)
