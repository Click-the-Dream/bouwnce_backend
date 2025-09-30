"""fixed: PostgreSQL AsyncPgEnum type requires a name.


Revision ID: 567c4d0df1fb
Revises: c927b3c9e6a0
Create Date: 2025-09-17 12:31:44.315652

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "567c4d0df1fb"
down_revision: Union[str, Sequence[str], None] = "c927b3c9e6a0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
