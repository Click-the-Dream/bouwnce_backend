"""empty message

Revision ID: f3539b2bb971
Revises: 2f88185dfd6c, 60f604fd10bd
Create Date: 2026-05-24 21:27:26.257092

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f3539b2bb971'
down_revision: Union[str, Sequence[str], None] = ('2f88185dfd6c', '60f604fd10bd')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
