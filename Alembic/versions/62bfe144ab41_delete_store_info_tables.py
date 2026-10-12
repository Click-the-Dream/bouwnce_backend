"""delete store_info tables

Revision ID: 62bfe144ab41
Revises: 8001140c8b1d
Create Date: 2025-10-29 11:35:07.722458

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "62bfe144ab41"
down_revision: str | Sequence[str] | None = "8001140c8b1d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_table("store_info")


def downgrade() -> None:
    """Downgrade schema."""
    pass
