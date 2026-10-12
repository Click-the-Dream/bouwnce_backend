"""create newsletter table

Revision ID: 24ce8a945ef5
Revises: 24eddf7b8fa2
Create Date: 2026-04-22 10:48:35.757898

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "24ce8a945ef5"
down_revision: str | Sequence[str] | None = "24eddf7b8fa2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
