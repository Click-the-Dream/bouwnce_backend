"""merge heads after order worker migration

Revision ID: 45affa483b69
Revises: 52ce096d0c9d, 9f5ffd19a5d4
Create Date: 2026-04-06 16:07:22.532613

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '45affa483b69'
down_revision: Union[str, Sequence[str], None] = ('52ce096d0c9d', '9f5ffd19a5d4')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
