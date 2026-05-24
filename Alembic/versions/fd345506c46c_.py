"""empty message

Revision ID: fd345506c46c
Revises: 7c1a7e2d4b90, ec695275d4b5
Create Date: 2026-05-22 21:42:02.505952

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "fd345506c46c"
down_revision: Union[str, Sequence[str], None] = ("7c1a7e2d4b90", "ec695275d4b5")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
