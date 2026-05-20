"""empty message

Revision ID: e315639d45c4
Revises: b6811a2a7129, fcd5de1a1e10
Create Date: 2026-05-20 08:35:59.630897

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e315639d45c4'
down_revision: Union[str, Sequence[str], None] = ('b6811a2a7129', 'fcd5de1a1e10')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
