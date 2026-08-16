"""add web_push_subscriptions table

Revision ID: c4d8a9e1b7f2
Revises: 3c7915e9c904
Create Date: 2026-08-16 15:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4d8a9e1b7f2"
down_revision: str | Sequence[str] | None = "3c7915e9c904"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "web_push_subscriptions",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("endpoint", sa.String(), nullable=False),
        sa.Column("p256dh", sa.String(), nullable=False),
        sa.Column("auth", sa.String(), nullable=False),
        sa.Column("expiration_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("endpoint", name="web_push_subscriptions_endpoint_key"),
    )
    op.create_index(
        op.f("ix_web_push_subscriptions_user_id"),
        "web_push_subscriptions",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f("ix_web_push_subscriptions_user_id"),
        table_name="web_push_subscriptions",
    )
    op.drop_table("web_push_subscriptions")
