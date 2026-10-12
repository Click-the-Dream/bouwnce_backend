"""add user attendance table

Revision ID: 8cc5d78af0c3
Revises: a0f44fa24a69
Create Date: 2026-07-17 00:13:21.792809

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "8cc5d78af0c3"
down_revision: str | Sequence[str] | None = "a0f44fa24a69"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
