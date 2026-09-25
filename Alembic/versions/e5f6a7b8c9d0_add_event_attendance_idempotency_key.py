"""add idempotency key to event attendance checkout

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e5f6a7b8c9d0"
down_revision: str | Sequence[str] | None = "d4e5f6a7b8c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "user_event_attendance",
        sa.Column("idempotency_key", sa.String(), nullable=True),
    )
    op.create_index(
        "ix_user_event_attendance_idempotency_key",
        "user_event_attendance",
        ["idempotency_key"],
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "ix_user_event_attendance_idempotency_key",
        table_name="user_event_attendance",
    )
    op.drop_column("user_event_attendance", "idempotency_key")
