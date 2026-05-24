"""empty message

Revision ID: b6811a2a7129
Revises: 8ab6e03fb2c6, 8f1c3b0d9a21
Create Date: 2026-05-14 16:42:40.153445

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b6811a2a7129"
down_revision: Union[str, Sequence[str], None] = "8f1c3b0d9a21"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
