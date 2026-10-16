from __future__ import annotations

from sqlalchemy import UUID, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.basemodel import BaseModel


class EventGroup(BaseModel):
    """One optional chat group linked to an event."""

    __tablename__ = "event_groups"

    event_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("outing_events.id", ondelete="CASCADE"),
        nullable=False,
    )
    group_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("groups.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_by: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("event_id", name="uq_event_groups_event_id"),
        UniqueConstraint("group_id", name="uq_event_groups_group_id"),
    )
