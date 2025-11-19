"""remove the non nullable in tranasaction_type in wallet_transactions table

Revision ID: 6bbeff748325
Revises: f849dd5bc875
Create Date: 2025-10-29 12:50:33.151332

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6bbeff748325"
down_revision: Union[str, Sequence[str], None] = "f849dd5bc875"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
