"""Merge caption into body and drop caption column.

Revision ID: 1d3c7a8b9e20
Revises: 9b2f6f0a1c7d
Create Date: 2026-05-23
"""

from alembic import op
import sqlalchemy as sa


revision = "1d3c7a8b9e20"
down_revision = "9b2f6f0a1c7d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Backfill: if body is empty, use caption as body
    op.execute(
        """
        UPDATE messages
        SET body = caption
        WHERE (body IS NULL OR body = '') AND caption IS NOT NULL
        """
    )
    op.drop_column("messages", "caption")


def downgrade() -> None:
    op.add_column("messages", sa.Column("caption", sa.String(), nullable=True))
    # Best-effort: copy body into caption for media messages
    op.execute(
        """
        UPDATE messages
        SET caption = body
        WHERE caption IS NULL AND body IS NOT NULL AND body <> ''
        """
    )

