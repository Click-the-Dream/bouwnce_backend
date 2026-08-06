"""Merge performance indexes heads

Revision ID: 9b4d2c7a5e81
Revises: a7e3b5c9d1f2, 3c7915e9c904
Create Date: 2026-08-04

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "9b4d2c7a5e81"
down_revision = ("a7e3b5c9d1f2", "3c7915e9c904")
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Merge point only (no-op).
    op.execute("SELECT 1")


def downgrade() -> None:
    # Downgrade is also a no-op; Alembic will split the graph back to the two heads.
    op.execute("SELECT 1")
