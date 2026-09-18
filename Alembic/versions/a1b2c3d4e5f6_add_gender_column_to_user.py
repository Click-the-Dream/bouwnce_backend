"""add gender column to user

Revision ID: a1b2c3d4e5f6
Revises: b2c8d4e6f012
Create Date: 2026-09-01 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "b2c8d4e6f012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    user_gender_enum = sa.Enum("male", "female", "other", name="user_gender_enum")
    user_gender_enum.create(op.get_bind(), checkfirst=True)

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(sa.Column("gender", sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("gender")

    sa.Enum(name="user_gender_enum").drop(op.get_bind(), checkfirst=True)
