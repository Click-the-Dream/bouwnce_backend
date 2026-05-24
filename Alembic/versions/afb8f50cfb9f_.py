"""empty message

Revision ID: afb8f50cfb9f
Revises: 2cb35a760ae0, c8f4a2d1e6b7
Create Date: 2026-05-23 12:58:19.606318

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "afb8f50cfb9f"
down_revision: Union[str, Sequence[str], None] = ("2cb35a760ae0", "c8f4a2d1e6b7")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
