"""Merging Heads 

Revision ID: 5a8ae401c1a3
Revises: d32f7dadfb1d, e03090a3d31d
Create Date: 2026-01-29 17:15:58.928961

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5a8ae401c1a3'
down_revision: Union[str, Sequence[str], None] = ('d32f7dadfb1d', 'e03090a3d31d')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
