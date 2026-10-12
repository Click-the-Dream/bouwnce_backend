"""Fixing alembic

Revision ID: 2d1cc668514a
Revises: 3dd05fe3984c
Create Date: 2026-07-14 21:41:48.801460

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "2d1cc668514a"
down_revision: str | Sequence[str] | None = "3dd05fe3984c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
