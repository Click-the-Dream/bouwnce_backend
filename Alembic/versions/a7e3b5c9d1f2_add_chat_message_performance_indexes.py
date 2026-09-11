"""Add chat message performance indexes

Revision ID: a7e3b5c9d1f2
Revises: c8f4a2d1e6b7
Create Date: 2026-08-04

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a7e3b5c9d1f2"
down_revision: str | Sequence[str] | None = "c8f4a2d1e6b7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # CREATE INDEX CONCURRENTLY cannot run inside a transaction, so wrap in an
    # autocommit block. This avoids blocking live chat writes on a large table.
    with op.get_context().autocommit_block():
        # Unread counts / mark-as-read filter heavily on recipient_id + read_at IS NULL.
        op.create_index(
            op.f("ix_messages_recipient_id"),
            "messages",
            ["recipient_id"],
            unique=False,
            postgresql_concurrently=True,
        )
        op.create_index(
            "ix_messages_recipient_unread",
            "messages",
            ["recipient_id"],
            unique=False,
            postgresql_where=sa.text("read_at IS NULL"),
            postgresql_concurrently=True,
        )
        # Message pages are `WHERE conversation_id = X ORDER BY created_at DESC`.
        op.create_index(
            op.f("ix_messages_conversation_created"),
            "messages",
            ["conversation_id", "created_at"],
            unique=False,
            postgresql_concurrently=True,
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.drop_index(
            op.f("ix_messages_conversation_created"),
            table_name="messages",
            postgresql_concurrently=True,
        )
        op.drop_index(
            "ix_messages_recipient_unread",
            table_name="messages",
            postgresql_concurrently=True,
        )
        op.drop_index(
            op.f("ix_messages_recipient_id"),
            table_name="messages",
            postgresql_concurrently=True,
        )
