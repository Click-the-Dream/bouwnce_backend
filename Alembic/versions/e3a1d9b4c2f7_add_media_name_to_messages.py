"""Add media_name to messages

Revision ID: e3a1d9b4c2f7
Revises: d4c7a1b2e9f0
Create Date: 2026-05-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e3a1d9b4c2f7"
down_revision: str | Sequence[str] | None = "d4c7a1b2e9f0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("messages", sa.Column("media_name", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("messages", "media_name")

