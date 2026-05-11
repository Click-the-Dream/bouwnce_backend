"""add platform to waitlist model and profile_pic to user model

Revision ID: a4a3097f2815
Revises: 2c0f3a9c2d1b
Create Date: 2026-05-10 04:46:10.028618

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a4a3097f2815'
down_revision: Union[str, Sequence[str], None] = '2c0f3a9c2d1b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
