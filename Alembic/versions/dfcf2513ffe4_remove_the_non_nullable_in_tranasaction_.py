"""remove the non nullable in tranasaction_type in wallet_transactions table

Revision ID: dfcf2513ffe4
Revises: 6bbeff748325
Create Date: 2025-10-29 12:51:06.851005

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "dfcf2513ffe4"
down_revision: str | Sequence[str] | None = "6bbeff748325"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
