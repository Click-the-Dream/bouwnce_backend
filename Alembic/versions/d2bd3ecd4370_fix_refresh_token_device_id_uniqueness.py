"""Fix refresh token device_id uniqueness

Revision ID: d2bd3ecd4370
Revises: 6b0c2f9a7d1a
Create Date: 2026-04-25 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d2bd3ecd4370"
down_revision: Union[str, Sequence[str], None] = "6b0c2f9a7d1a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _constraint_exists(table_name: str, constraint_name: str) -> bool:
    bind = op.get_bind()
    schema = bind.dialect.default_schema_name
    stmt = sa.text(
        """
        SELECT 1
        FROM pg_constraint c
        JOIN pg_class t ON t.oid = c.conrelid
        JOIN pg_namespace n ON n.oid = t.relnamespace
        WHERE n.nspname = :schema
          AND t.relname = :table_name
          AND c.conname = :constraint_name
        LIMIT 1
        """
    )
    return (
        bind.execute(
            stmt,
            {
                "schema": schema,
                "table_name": table_name,
                "constraint_name": constraint_name,
            },
        ).first()
        is not None
    )


def upgrade() -> None:
    """Upgrade schema."""
    # Some environments may not have the legacy constraint name; be resilient.
    if _constraint_exists("refresh_tokens", "refresh_tokens_device_id_key"):
        op.drop_constraint(
            "refresh_tokens_device_id_key", "refresh_tokens", type_="unique"
        )
    if not _constraint_exists("refresh_tokens", "uix_refresh_tokens_user_id_device_id"):
        op.create_unique_constraint(
            "uix_refresh_tokens_user_id_device_id",
            "refresh_tokens",
            ["user_id", "device_id"],
        )


def downgrade() -> None:
    """Downgrade schema."""
    if _constraint_exists("refresh_tokens", "uix_refresh_tokens_user_id_device_id"):
        op.drop_constraint(
            "uix_refresh_tokens_user_id_device_id", "refresh_tokens", type_="unique"
        )
    if not _constraint_exists("refresh_tokens", "refresh_tokens_device_id_key"):
        op.create_unique_constraint(
            "refresh_tokens_device_id_key",
            "refresh_tokens",
            ["device_id"],
        )
