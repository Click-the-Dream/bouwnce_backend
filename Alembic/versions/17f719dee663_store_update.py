"""store update

Revision ID: 17f719dee663
Revises: b3c765382398
Create Date: 2025-10-01 13:28:06.208174

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "17f719dee663"
down_revision: str | Sequence[str] | None = "b3c765382398"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
