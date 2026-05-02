"""Repair user_wallets and refunds tables

Revision ID: 6b0c2f9a7d1a
Revises: 515f208cdc76
Create Date: 2026-04-22

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "6b0c2f9a7d1a"
down_revision: str | Sequence[str] | None = "515f208cdc76"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return inspector.has_table(table_name)


def upgrade() -> None:
    sa.Enum("pending", "released", "failed", name="refund_status").create(
        op.get_bind(), checkfirst=True
    )

    if not _table_exists("user_wallets"):
        op.create_table(
            "user_wallets",
            sa.Column("user_id", sa.UUID(), nullable=False),
            sa.Column("balance", sa.Float(), nullable=False, server_default="0"),
            sa.Column("pending_balance", sa.Float(), nullable=False, server_default="0"),
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "is_deleted",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id"),
        )

    if not _table_exists("refunds"):
        op.create_table(
            "refunds",
            sa.Column("wallet_id", sa.UUID(), nullable=False),
            sa.Column("order_item_id", sa.UUID(), nullable=False),
            sa.Column("amount", sa.Float(), nullable=False),
            sa.Column(
                "status",
                postgresql.ENUM(
                    "pending",
                    "released",
                    "failed",
                    name="refund_status",
                    create_type=False,
                ),
                nullable=False,
            ),
            sa.Column("release_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "is_deleted",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
            sa.ForeignKeyConstraint(
                ["order_item_id"], ["order_items.id"], ondelete="SET NULL"
            ),
            sa.ForeignKeyConstraint(["wallet_id"], ["user_wallets.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )


def downgrade() -> None:
    if _table_exists("refunds"):
        op.drop_table("refunds")
    if _table_exists("user_wallets"):
        op.drop_table("user_wallets")
    sa.Enum("pending", "released", "failed", name="refund_status").drop(
        op.get_bind(), checkfirst=True
    )

