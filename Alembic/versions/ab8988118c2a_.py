"""empty message

Revision ID: ab8988118c2a
Revises: 45affa483b69, f77f7f8173e4
Create Date: 2026-05-02 15:42:17.667077

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ab8988118c2a"
down_revision: Union[str, Sequence[str], None] = ("45affa483b69", "f77f7f8173e4")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
