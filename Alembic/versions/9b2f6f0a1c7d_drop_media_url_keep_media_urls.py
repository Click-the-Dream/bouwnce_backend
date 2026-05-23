"""Drop media_url and keep media_urls

Revision ID: 9b2f6f0a1c7d
Revises: 7c1a7e2d4b90
Create Date: 2026-05-23
"""

from alembic import op
import sqlalchemy as sa


revision = "9b2f6f0a1c7d"
down_revision = "7c1a7e2d4b90"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # If media_urls is null but media_url exists, backfill list first.
    op.execute(
        """
        UPDATE messages
        SET media_urls = jsonb_build_array(media_url)
        WHERE media_urls IS NULL AND media_url IS NOT NULL
        """
    )
    op.drop_column("messages", "media_url")


def downgrade() -> None:
    op.add_column("messages", sa.Column("media_url", sa.String(), nullable=True))
    # Best-effort: copy first item into media_url
    op.execute(
        """
        UPDATE messages
        SET media_url = CASE
            WHEN media_urls IS NULL THEN NULL
            WHEN jsonb_typeof(media_urls) != 'array' THEN NULL
            WHEN jsonb_array_length(media_urls) = 0 THEN NULL
            ELSE (media_urls->>0)
        END
        """
    )

