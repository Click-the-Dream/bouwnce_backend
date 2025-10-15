"""First Commit

Revision ID: 9e60af40a441
Revises: 46c75220fe7e
Create Date: 2025-09-17 10:59:39.741096

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9e60af40a441'
down_revision: Union[str, Sequence[str], None] = '46c75220fe7e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
