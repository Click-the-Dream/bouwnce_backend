"""store update

Revision ID: d1ec4d316d2f
Revises: 17f719dee663
Create Date: 2025-10-01 13:31:34.535773

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "d1ec4d316d2f"
down_revision: str | Sequence[str] | None = "17f719dee663"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
