"""Optimization of suborder db

Revision ID: d88bfc3f3121
Revises: b838baf21962
Create Date: 2026-01-07 01:44:12.124811

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd88bfc3f3121'
down_revision: Union[str, Sequence[str], None] = 'b838baf21962'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
