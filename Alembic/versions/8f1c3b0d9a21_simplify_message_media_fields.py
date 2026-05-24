"""Simplify message media fields

Revision ID: 8f1c3b0d9a21
Revises: 6a2d2b1f8c4e
Create Date: 2026-05-14
"""

import sqlalchemy as sa
from alembic import op

revision = "8f1c3b0d9a21"
down_revision = "6a2d2b1f8c4e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add minimal fields
    op.add_column("messages", sa.Column("media_url", sa.String(), nullable=True))
    op.add_column("messages", sa.Column("media_type", sa.String(), nullable=True))

    # Backfill from old columns if they exist
    op.execute(
        """
        UPDATE messages
        SET media_url = COALESCE(image_url, video_url, file_url),
            media_type = CASE
                WHEN image_url IS NOT NULL THEN 'image'
                WHEN video_url IS NOT NULL THEN 'video'
                WHEN file_url IS NOT NULL THEN 'file'
                ELSE media_type
            END
        WHERE media_url IS NULL
        """
    )

    # Drop expanded columns
    op.drop_column("messages", "image_url")
    op.drop_column("messages", "video_url")
    op.drop_column("messages", "file_url")
    op.drop_column("messages", "file_name")
    op.drop_column("messages", "file_mime")
    op.drop_column("messages", "file_size")


def downgrade() -> None:
    op.add_column("messages", sa.Column("file_size", sa.Integer(), nullable=True))
    op.add_column("messages", sa.Column("file_mime", sa.String(), nullable=True))
    op.add_column("messages", sa.Column("file_name", sa.String(), nullable=True))
    op.add_column("messages", sa.Column("file_url", sa.String(), nullable=True))
    op.add_column("messages", sa.Column("video_url", sa.String(), nullable=True))
    op.add_column("messages", sa.Column("image_url", sa.String(), nullable=True))

    op.execute(
        """
        UPDATE messages
        SET image_url = CASE WHEN media_type = 'image' THEN media_url ELSE NULL END,
            video_url = CASE WHEN media_type = 'video' THEN media_url ELSE NULL END,
            file_url  = CASE WHEN media_type = 'file'  THEN media_url ELSE NULL END
        """
    )

    op.drop_column("messages", "media_type")
    op.drop_column("messages", "media_url")
