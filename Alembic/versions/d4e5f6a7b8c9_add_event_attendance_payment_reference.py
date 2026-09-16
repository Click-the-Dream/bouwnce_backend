"""add Paystack checkout fields to event attendance

Revision ID: d4e5f6a7b8c9
Revises: a1b2c3d4e5f6
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: str | Sequence[str] | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "user_event_attendance", sa.Column("payment_reference", sa.String(), nullable=True)
    )
    op.add_column("user_event_attendance", sa.Column("payment_url", sa.String(), nullable=True))
    op.create_index(
        "ix_user_event_attendance_payment_reference",
        "user_event_attendance",
        ["payment_reference"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_user_event_attendance_payment_reference", table_name="user_event_attendance")
    op.drop_column("user_event_attendance", "payment_url")
    op.drop_column("user_event_attendance", "payment_reference")
