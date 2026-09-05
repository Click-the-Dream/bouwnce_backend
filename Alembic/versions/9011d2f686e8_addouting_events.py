"""addouting_events

Revision ID: 9011d2f686e8
Revises: fdae71e2ab28
Create Date: 2026-07-14 21:35:22.062600

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9011d2f686e8'
down_revision: Union[str, Sequence[str], None] = 'fdae71e2ab28'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
