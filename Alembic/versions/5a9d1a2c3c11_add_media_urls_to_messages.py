"""Add media_urls to messages

Revision ID: 5a9d1a2c3c11
Revises: b6811a2a7129
Create Date: 2026-05-21
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "5a9d1a2c3c11"
down_revision = "b6811a2a7129"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "messages",
        sa.Column("media_urls", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    # Backfill: if media_url exists, set media_urls=[media_url]
    op.execute(
        """
        UPDATE messages
        SET media_urls = jsonb_build_array(media_url)
        WHERE media_urls IS NULL AND media_url IS NOT NULL
        """
    )


def downgrade() -> None:
    op.drop_column("messages", "media_urls")
