"""Make outing event link nullable

Revision ID: d47b2c1a8e91
Revises: f0fc34f9542f
Create Date: 2026-07-21 16:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "d47b2c1a8e91"
down_revision: Union[str, Sequence[str], None] = "f0fc34f9542f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("outing_events", schema=None) as batch_op:
        batch_op.alter_column(
            "link",
            existing_type=sa.String(),
            nullable=True,
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("outing_events", schema=None) as batch_op:
        batch_op.alter_column(
            "link",
            existing_type=sa.String(),
            nullable=False,
        )
