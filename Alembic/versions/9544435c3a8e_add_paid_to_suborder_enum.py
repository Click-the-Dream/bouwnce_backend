"""add paid to suborder_enum

Revision ID: 9544435c3a8e
Revises: af7f3ae39b0d
Create Date: 2025-11-28 17:32:58.491452

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9544435c3a8e"
down_revision: Union[str, Sequence[str], None] = "af7f3ae39b0d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
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
