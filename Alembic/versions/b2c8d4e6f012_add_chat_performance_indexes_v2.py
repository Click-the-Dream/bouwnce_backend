"""Add chat performance indexes v2

Missing indexes that slow down:
- get_conversation_partner_ids (OR query on user_a_id/user_b_id)
- list_conversations (OR query + ORDER BY last_message_at)
- get_unread_summary notifications (user_id + read_at + is_deleted)
- list_conversations unread counts (conversation_id + recipient_id + read_at)

Revision ID: b2c8d4e6f012
Revises: a7e3b5c9d1f2
Create Date: 2026-08-20

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2c8d4e6f012"
down_revision: str | Sequence[str] | None = ("9b4d2c7a5e81", "c4d8a9e1b7f2")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        # Covering index for get_conversation_partner_ids and list_conversations.
        # The OR query (user_a_id = X OR user_b_id = X) can use two separate
        # B-tree indexes, but a GiST index on both columns is faster for OR.
        # Instead, we create a composite covering index that includes
        # last_message_at for list_conversations ORDER BY.
        op.create_index(
            "ix_conversations_user_a_last_msg",
            "conversations",
            ["user_a_id", sa.text("last_message_at DESC")],
            unique=False,
            if_not_exists=True,
            postgresql_concurrently=True,
        )
        op.create_index(
            "ix_conversations_user_b_last_msg",
            "conversations",
            ["user_b_id", sa.text("last_message_at DESC")],
            unique=False,
            if_not_exists=True,
            postgresql_concurrently=True,
        )

        # Partial index for notification unread counts.
        # Query: WHERE user_id = X AND read_at IS NULL AND is_deleted = FALSE
        op.create_index(
            "ix_notifications_user_unread",
            "notifications",
            ["user_id"],
            unique=False,
            if_not_exists=True,
            postgresql_where=sa.text("read_at IS NULL AND is_deleted = false"),
            postgresql_concurrently=True,
        )

        # Partial index for message unread counts in list_conversations.
        # Query: WHERE conversation_id IN (...) AND recipient_id = X AND read_at IS NULL
        op.create_index(
            "ix_messages_convo_recipient_unread",
            "messages",
            ["conversation_id", "recipient_id"],
            unique=False,
            if_not_exists=True,
            postgresql_where=sa.text("read_at IS NULL"),
            postgresql_concurrently=True,
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.drop_index(
            "ix_messages_convo_recipient_unread",
            table_name="messages",
            postgresql_concurrently=True,
        )
        op.drop_index(
            "ix_notifications_user_unread",
            table_name="notifications",
            postgresql_concurrently=True,
        )
        op.drop_index(
            "ix_conversations_user_b_last_msg",
            table_name="conversations",
            postgresql_concurrently=True,
        )
        op.drop_index(
            "ix_conversations_user_a_last_msg",
            table_name="conversations",
            postgresql_concurrently=True,
        )
