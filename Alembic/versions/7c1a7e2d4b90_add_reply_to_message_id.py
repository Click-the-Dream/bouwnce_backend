"""Add reply_to_message_id to messages

Revision ID: 7c1a7e2d4b90
Revises: 5a9d1a2c3c11
Create Date: 2026-05-21
"""

import sqlalchemy as sa
from alembic import op

revision = "7c1a7e2d4b90"
down_revision = "5a9d1a2c3c11"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "messages",
        sa.Column("reply_to_message_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_messages_reply_to_message_id",
        "messages",
        "messages",
        ["reply_to_message_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_messages_reply_to_message_id", "messages", type_="foreignkey"
    )
    op.drop_column("messages", "reply_to_message_id")
