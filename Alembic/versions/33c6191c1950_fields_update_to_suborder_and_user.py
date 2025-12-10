"""fields update to suborder and user

Revision ID: 33c6191c1950
Revises: 7071ee03ddca
Create Date: 2025-12-10 01:57:02.234464

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '33c6191c1950'
down_revision: Union[str, Sequence[str], None] = '7071ee03ddca'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
