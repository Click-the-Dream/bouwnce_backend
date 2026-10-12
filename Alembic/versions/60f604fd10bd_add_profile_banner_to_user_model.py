"""add profile_banner to user model"


Revision ID: 60f604fd10bd
Revises: 84de23a34a03
Create Date: 2026-05-24 21:25:19.485007

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "60f604fd10bd"
down_revision: str | Sequence[str] | None = "84de23a34a03"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
