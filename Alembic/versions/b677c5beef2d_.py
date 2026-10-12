"""empty message

Revision ID: b677c5beef2d
Revises: 0309b4f8e988, b2c7d9a3e4f1
Create Date: 2026-05-25 13:28:11.462039

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "b677c5beef2d"
down_revision: str | Sequence[str] | None = ("0309b4f8e988", "b2c7d9a3e4f1")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
