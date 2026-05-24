"""empty message

Revision ID: f77f7f8173e4
Revises: 6ac704c2b309, d2bd3ecd4370
Create Date: 2026-05-02 15:26:13.468896

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f77f7f8173e4"
down_revision: Union[str, Sequence[str], None] = ("6ac704c2b309", "d2bd3ecd4370")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
