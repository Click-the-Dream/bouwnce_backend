"""changed user_id column to store_id in wallet table

Revision ID: 179ac2fbd663
Revises: ab80112bf8cf
Create Date: 2025-10-28 21:47:40.918352

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "179ac2fbd663"
down_revision: Union[str, Sequence[str], None] = "ab80112bf8cf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
