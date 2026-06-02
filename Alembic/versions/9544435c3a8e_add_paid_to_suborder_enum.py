"""add paid to suborder_enum

Revision ID: 9544435c3a8e
Revises: af7f3ae39b0d
Create Date: 2025-11-28 17:32:58.491452

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9544435c3a8e"
down_revision: Union[str, Sequence[str], None] = "af7f3ae39b0d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _enum_exists(enum_name: str) -> bool:
    bind = op.get_bind()
    return (
        bind.execute(
            sa.text(
                """
                SELECT 1
                FROM pg_type t
                JOIN pg_namespace n ON n.oid = t.typnamespace
                WHERE n.nspname = current_schema()
                  AND t.typname = :enum_name
                LIMIT 1
                """
            ),
            {"enum_name": enum_name},
        ).first()
        is not None
    )


def upgrade() -> None:
    """Upgrade schema."""
    if not _enum_exists("suborder_status_enum"):
        sa.Enum(
            "pending",
            "paid",
            "accepted",
            "declined",
            "shipped",
            "delivered",
            "cancelled",
            name="suborder_status_enum",
        ).create(op.get_bind(), checkfirst=True)
    op.execute("ALTER TYPE suborder_status_enum ADD VALUE IF NOT EXISTS 'pending'")
    op.execute("ALTER TYPE suborder_status_enum ADD VALUE IF NOT EXISTS 'paid'")
    op.execute("ALTER TYPE suborder_status_enum ADD VALUE IF NOT EXISTS 'accepted'")
    op.execute("ALTER TYPE suborder_status_enum ADD VALUE IF NOT EXISTS 'declined'")
    op.execute("ALTER TYPE suborder_status_enum ADD VALUE IF NOT EXISTS 'delivered'")
    op.execute("ALTER TYPE suborder_status_enum ADD VALUE IF NOT EXISTS 'shipped'")
    op.execute("ALTER TYPE suborder_status_enum ADD VALUE IF NOT EXISTS 'cancelled'")


def downgrade() -> None:
    """Downgrade schema."""
    pass
