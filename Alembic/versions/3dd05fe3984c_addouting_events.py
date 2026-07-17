"""addouting_events

Revision ID: 3dd05fe3984c
Revises: 9011d2f686e8
Create Date: 2026-07-14 21:38:45.776031

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3dd05fe3984c'
down_revision: Union[str, Sequence[str], None] = '9011d2f686e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
