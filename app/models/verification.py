from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID as UUID_Type

from sqlalchemy import UUID, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import BaseModel

if TYPE_CHECKING:
    from app.models import User


class Verification(BaseModel):
    __tablename__ = "verifications"

    type: Mapped[str] = mapped_column(String, nullable=False)
    user_id: Mapped[UUID_Type] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    id_number: Mapped[str] = mapped_column(String, nullable=False)
    picture: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(
        Enum("pending", "approved", "rejected", name="status_enum"),
        nullable=False,
        default="pending",
    )

    user: Mapped[User] = relationship(back_populates="verification", uselist=False)
