"""Price removal

Revision ID: 3c7915e9c904
Revises: 061687c6dc2a
Create Date: 2026-07-21 15:52:05.096109

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3c7915e9c904'
down_revision: Union[str, Sequence[str], None] = '061687c6dc2a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
