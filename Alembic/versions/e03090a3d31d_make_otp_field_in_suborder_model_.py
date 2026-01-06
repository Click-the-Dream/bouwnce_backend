"""make otp field in suborder model optional


Revision ID: e03090a3d31d
Revises: 21f8566207fc
Create Date: 2025-12-22 03:29:25.900745

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e03090a3d31d"
down_revision: Union[str, Sequence[str], None] = "21f8566207fc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
