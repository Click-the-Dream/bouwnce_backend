"""add platform to waitlist model and profile_pic to user model

Revision ID: 8ab6e03fb2c6
Revises: a4a3097f2815
Create Date: 2026-05-10 04:49:32.400345

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8ab6e03fb2c6"
down_revision: Union[str, Sequence[str], None] = "a4a3097f2815"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
