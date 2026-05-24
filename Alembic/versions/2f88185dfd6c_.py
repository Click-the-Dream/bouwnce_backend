"""empty message

Revision ID: 2f88185dfd6c
Revises: 284346085d2a, 84de23a34a03
Create Date: 2026-05-24 21:01:36.565422

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2f88185dfd6c"
down_revision: Union[str, Sequence[str], None] = ("284346085d2a", "84de23a34a03")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
