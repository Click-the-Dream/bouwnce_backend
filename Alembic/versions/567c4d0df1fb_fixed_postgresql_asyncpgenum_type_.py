"""fixed: PostgreSQL AsyncPgEnum type requires a name.


Revision ID: 567c4d0df1fb
Revises: c927b3c9e6a0
Create Date: 2025-09-17 12:31:44.315652

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "567c4d0df1fb"
down_revision: str | Sequence[str] | None = "c927b3c9e6a0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
