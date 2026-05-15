"""Restore missing revision referenced by staging DB.

Revision ID: fcd5de1a1e10
Revises: 2c0f3a9c2d1b
Create Date: 2026-05-14
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "fcd5de1a1e10"
down_revision: Union[str, Sequence[str], None] = "2c0f3a9c2d1b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    This revision was missing from the repository but exists in the database's
    alembic_version table in some environments.

    It is intentionally a no-op so we can continue migrations from the existing
    database state.
    """
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

