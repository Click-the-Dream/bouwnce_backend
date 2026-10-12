"""merge store and store_info tables

Revision ID: f849dd5bc875
Revises: 763101b50b76
Create Date: 2025-10-29 11:43:56.959167

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "f849dd5bc875"
down_revision: str | Sequence[str] | None = "763101b50b76"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
