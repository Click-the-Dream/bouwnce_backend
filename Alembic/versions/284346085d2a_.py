"""empty message

Revision ID: 284346085d2a
Revises: afb8f50cfb9f, d4c7a1b2e9f0
Create Date: 2026-05-23 16:51:15.645056

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '284346085d2a'
down_revision: Union[str, Sequence[str], None] = ('afb8f50cfb9f', 'd4c7a1b2e9f0')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
