"""empty message

Revision ID: b39d8a61427d
Revises: c3f0b6f6f9a1, dfcf2513ffe4
Create Date: 2026-06-01 02:06:04.176399

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "b39d8a61427d"
down_revision: str | Sequence[str] | None = ("c3f0b6f6f9a1", "dfcf2513ffe4")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
