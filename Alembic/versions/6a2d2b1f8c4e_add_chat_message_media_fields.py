"""Add media fields to messages

Revision ID: 6a2d2b1f8c4e
Revises: 2c0f3a9c2d1b
Create Date: 2026-05-14
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "6a2d2b1f8c4e"
down_revision = "2c0f3a9c2d1b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("messages", sa.Column("caption", sa.String(), nullable=True))
    op.add_column("messages", sa.Column("image_url", sa.String(), nullable=True))
    op.add_column("messages", sa.Column("video_url", sa.String(), nullable=True))
    op.add_column("messages", sa.Column("file_url", sa.String(), nullable=True))
    op.add_column("messages", sa.Column("file_name", sa.String(), nullable=True))
    op.add_column("messages", sa.Column("file_mime", sa.String(), nullable=True))
    op.add_column("messages", sa.Column("file_size", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("messages", "file_size")
    op.drop_column("messages", "file_mime")
    op.drop_column("messages", "file_name")
    op.drop_column("messages", "file_url")
    op.drop_column("messages", "video_url")
    op.drop_column("messages", "image_url")
    op.drop_column("messages", "caption")

