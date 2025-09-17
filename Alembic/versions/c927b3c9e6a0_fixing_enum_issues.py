"""Fixing Enum Issues

Revision ID: c927b3c9e6a0
Revises: 9e60af40a441
Create Date: 2025-09-17 11:18:00.350123

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c927b3c9e6a0'
down_revision: Union[str, Sequence[str], None] = '9e60af40a441'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
