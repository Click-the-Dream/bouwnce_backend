"""empty message

Revision ID: 2cb35a760ae0
Revises: 1d3c7a8b9e20, fd345506c46c
Create Date: 2026-05-23 12:37:05.447993

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2cb35a760ae0"
down_revision: Union[str, Sequence[str], None] = ("1d3c7a8b9e20", "fd345506c46c")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
