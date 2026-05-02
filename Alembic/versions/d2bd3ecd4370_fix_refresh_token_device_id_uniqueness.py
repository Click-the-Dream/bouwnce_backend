"""Fix refresh token device_id uniqueness

Revision ID: d2bd3ecd4370
Revises: 6b0c2f9a7d1a
Create Date: 2026-04-25 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "d2bd3ecd4370"
down_revision: Union[str, Sequence[str], None] = "6b0c2f9a7d1a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint("refresh_tokens_device_id_key", "refresh_tokens", type_="unique")
    op.create_unique_constraint(
        "uix_refresh_tokens_user_id_device_id",
        "refresh_tokens",
        ["user_id", "device_id"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "uix_refresh_tokens_user_id_device_id", "refresh_tokens", type_="unique"
    )
    op.create_unique_constraint(
        "refresh_tokens_device_id_key",
        "refresh_tokens",
        ["device_id"],
    )

