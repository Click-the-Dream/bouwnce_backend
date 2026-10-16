"""add idempotency key to event attendance checkout

Revision ID: 20261015_attendance_idempotency
Revises: e5f6a7b8c9d0
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "20261015_attendance_idempotency"
down_revision: str | Sequence[str] | None = "e5f6a7b8c9d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    columns = {
        column["name"] for column in inspector.get_columns("user_event_attendance")
    }
    indexes = {
        index["name"]: index for index in inspector.get_indexes("user_event_attendance")
    }
    index = indexes.get("ix_user_event_attendance_idempotency_key")

    if index is not None and (
        "idempotency_key" not in columns
        or index["column_names"] != ["idempotency_key"]
        or not index["unique"]
    ):
        raise RuntimeError(
            "The existing event-attendance idempotency index does not match "
            "the expected schema; refusing to modify it automatically."
        )

    if "idempotency_key" not in columns:
        op.add_column(
            "user_event_attendance",
            sa.Column("idempotency_key", sa.String(), nullable=True),
        )

    if index is None:
        op.create_index(
            "ix_user_event_attendance_idempotency_key",
            "user_event_attendance",
            ["idempotency_key"],
            unique=True,
            postgresql_where=sa.text("idempotency_key IS NOT NULL"),
        )


def downgrade() -> None:
    # The objects may predate this compatibility revision on deployed databases.
    pass
