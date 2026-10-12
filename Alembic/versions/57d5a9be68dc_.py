"""empty message

Revision ID: 57d5a9be68dc
Revises: 1a3fbb4c3478
Create Date: 2026-03-08 22:47:08.567970

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "57d5a9be68dc"
down_revision: str | Sequence[str] | None = "1a3fbb4c3478"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
