"""Ensure group-chat tables exist after resolving the legacy duplicate revision.

Revision ID: 20261015_reconcile_groups
Revises: 20261015_merge_event_heads
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "20261015_reconcile_groups"
down_revision: str | Sequence[str] | None = "20261015_merge_event_heads"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    group_tables = {"groups", "group_members", "group_messages"}
    present_tables = {
        table_name for table_name in group_tables if inspector.has_table(table_name)
    }

    if present_tables == group_tables:
        return
    if present_tables:
        missing_tables = sorted(group_tables - present_tables)
        raise RuntimeError(
            "Cannot safely reconcile the legacy group-chat schema because only "
            f"some expected tables exist. Missing: {', '.join(missing_tables)}"
        )

    op.create_table(
        "groups",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="groups_name_key"),
    )
    op.create_index("ix_groups_name", "groups", ["name"], unique=False)
    op.create_index("ix_groups_created_by", "groups", ["created_by"], unique=False)

    op.create_table(
        "group_members",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("group_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("invited_by", sa.UUID(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["invited_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("group_id", "user_id", name="uix_group_member"),
    )
    op.create_index(
        "ix_group_members_group_id", "group_members", ["group_id"], unique=False
    )
    op.create_index(
        "ix_group_members_user_id", "group_members", ["user_id"], unique=False
    )
    op.create_index("ix_group_members_role", "group_members", ["role"], unique=False)

    op.create_table(
        "group_messages",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("group_id", sa.UUID(), nullable=False),
        sa.Column("sender_id", sa.UUID(), nullable=False),
        sa.Column("body", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_edited", sa.Boolean(), nullable=False),
        sa.Column("media_type", sa.String(), nullable=True),
        sa.Column("media_urls", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "media_names",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("reply_to_message_id", sa.UUID(), nullable=True),
        sa.Column(
            "mentioned_user_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("read_count", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sender_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reply_to_message_id"], ["group_messages.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_group_messages_group_id", "group_messages", ["group_id"], unique=False
    )
    op.create_index(
        "ix_group_messages_sender_id", "group_messages", ["sender_id"], unique=False
    )
    op.create_index(
        "ix_group_messages_created_at", "group_messages", ["created_at"], unique=False
    )
    op.create_index(
        "ix_group_messages_reply_to",
        "group_messages",
        ["reply_to_message_id"],
        unique=False,
    )


def downgrade() -> None:
    # These tables may predate this compatibility revision and may contain data.
    pass
