"""add event group links

Revision ID: 20261015_event_groups
Revises: 20261015_reconcile_groups
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261015_event_groups"
down_revision: str | Sequence[str] | None = "20261015_reconcile_groups"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "event_groups",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("event_id", sa.UUID(), nullable=False),
        sa.Column("group_id", sa.UUID(), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["outing_events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id", name="uq_event_groups_event_id"),
        sa.UniqueConstraint("group_id", name="uq_event_groups_group_id"),
    )
    with op.get_context().autocommit_block():
        op.create_index(
            "ix_user_event_attendance_confirmed_event_user",
            "user_event_attendance",
            ["event_id", "user_id"],
            postgresql_where=sa.text(
                "payment_status = 'successful' "
                "AND attendance_status = 'confirmed' "
                "AND is_deleted = false"
            ),
            postgresql_concurrently=True,
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.drop_index(
            "ix_user_event_attendance_confirmed_event_user",
            table_name="user_event_attendance",
            postgresql_concurrently=True,
        )
    op.drop_table("event_groups")
