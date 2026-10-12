"""add profile banner to user table

Revision ID: 84de23a34a03
Revises: afb8f50cfb9f
Create Date: 2026-05-24 15:19:16.670271

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "84de23a34a03"
down_revision: str | Sequence[str] | None = "afb8f50cfb9f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
