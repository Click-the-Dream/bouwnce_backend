"""Merge heads

Revision ID: 5b2acbb6a20d
Revises: 33c6191c1950, f3bd4b2a414d
Create Date: 2025-12-10 02:04:05.974476

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "5b2acbb6a20d"
down_revision: str | Sequence[str] | None = ("33c6191c1950", "f3bd4b2a414d")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
