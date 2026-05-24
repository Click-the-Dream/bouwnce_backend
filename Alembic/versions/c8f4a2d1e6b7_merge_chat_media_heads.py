"""Merge chat media heads

Revision ID: c8f4a2d1e6b7
Revises: 1d3c7a8b9e20, 8f1c3b0d9a21
Create Date: 2026-05-23
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "c8f4a2d1e6b7"
down_revision = ("1d3c7a8b9e20", "8f1c3b0d9a21")
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Merge point only (no-op).
    op.execute("SELECT 1")


def downgrade() -> None:
    # Downgrade is also a no-op; Alembic will split the graph back to the two heads.
    op.execute("SELECT 1")
