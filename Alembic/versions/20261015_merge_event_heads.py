"""Merge event attendance and group-chat migration branches.

Revision ID: 20261015_merge_event_heads
Revises: f6a7b8c9d0e1, 20261015_attendance_idempotency
"""

from collections.abc import Sequence

revision: str = "20261015_merge_event_heads"
down_revision: str | Sequence[str] | None = (
    "f6a7b8c9d0e1",
    "20261015_attendance_idempotency",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
