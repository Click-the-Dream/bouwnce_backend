"""empty message

Revision ID: b677c5beef2d
Revises: 0309b4f8e988, b2c7d9a3e4f1
Create Date: 2026-05-25 13:28:11.462039

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b677c5beef2d"
down_revision: Union[str, Sequence[str], None] = ("0309b4f8e988", "b2c7d9a3e4f1")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
