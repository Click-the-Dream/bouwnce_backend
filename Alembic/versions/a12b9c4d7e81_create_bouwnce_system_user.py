"""Create Bouwnce system user

Revision ID: a12b9c4d7e81
Revises: e3a1d9b4c2f7
Create Date: 2026-05-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.core.config import settings


revision: str = "a12b9c4d7e81"
down_revision: str | Sequence[str] | None = "e3a1d9b4c2f7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


BOUWNCE_EMAIL = settings.BOUWNCE_SYSTEM_EMAIL
BOUWNCE_USERNAME = settings.BOUWNCE_SYSTEM_USERNAME
BOUWNCE_FULL_NAME = settings.BOUWNCE_SYSTEM_FULL_NAME


def upgrade() -> None:
    op.execute(sa.text('CREATE EXTENSION IF NOT EXISTS "pgcrypto"'))
    op.execute(
        sa.text(
            """
            INSERT INTO users (
                id,
                email,
                full_name,
                username,
                is_active,
                role,
                is_store_owner,
                created_at,
                updated_at,
                deleted_at,
                is_deleted
            )
            SELECT
                gen_random_uuid(),
                :email,
                :full_name,
                :username,
                TRUE,
                'user',
                FALSE,
                now(),
                now(),
                NULL,
                FALSE
            WHERE NOT EXISTS (SELECT 1 FROM users WHERE email = :email)
            """
        ).bindparams(
            email=BOUWNCE_EMAIL,
            full_name=BOUWNCE_FULL_NAME,
            username=BOUWNCE_USERNAME,
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text("DELETE FROM users WHERE email = :email").bindparams(email=BOUWNCE_EMAIL)
    )
