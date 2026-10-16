"""Add per-user message deletion and everyone-delete tombstones.

Revision ID: 20261016_message_mutations
Revises: 20261015_event_groups
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261016_message_mutations"
down_revision: str | Sequence[str] | None = "20261015_event_groups"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _create_deletion_table(table: str, message_table: str, unique_name: str) -> None:
    op.create_table(
        table,
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("message_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "is_deleted", sa.Boolean(), server_default=sa.false(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["message_id"], [f"{message_table}.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("message_id", "user_id", name=unique_name),
    )
    op.create_index(
        f"ix_{table}_user_message", table, ["user_id", "message_id"], unique=False
    )


def upgrade() -> None:
    op.add_column("messages", sa.Column("edited_at", sa.DateTime(timezone=True)))
    op.add_column(
        "messages",
        sa.Column("is_edited", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column(
        "messages",
        sa.Column("deleted_for_everyone_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "group_messages",
        sa.Column("deleted_for_everyone_at", sa.DateTime(timezone=True), nullable=True),
    )
    _create_deletion_table(
        "message_deletions", "messages", "uq_message_deletions_message_user"
    )
    _create_deletion_table(
        "group_message_deletions",
        "group_messages",
        "uq_group_message_deletions_message_user",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_group_message_deletions_user_message",
        table_name="group_message_deletions",
    )
    op.drop_table("group_message_deletions")
    op.drop_index("ix_message_deletions_user_message", table_name="message_deletions")
    op.drop_table("message_deletions")
    op.drop_column("group_messages", "deleted_for_everyone_at")
    op.drop_column("messages", "deleted_for_everyone_at")
    op.drop_column("messages", "is_edited")
    op.drop_column("messages", "edited_at")
