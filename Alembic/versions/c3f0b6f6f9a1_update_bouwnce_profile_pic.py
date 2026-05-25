"""Update Bouwnce system user profile picture.

Revision ID: c3f0b6f6f9a1
Revises: b677c5beef2d
Create Date: 2026-05-25 17:20:00.000000

"""

from __future__ import annotations

import os
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3f0b6f6f9a1"
down_revision: str | Sequence[str] | None = "b677c5beef2d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _bouwnce_identity() -> tuple[str, str, str]:
    email = os.getenv("BOUWNCE_SYSTEM_EMAIL", "support@bouwnce.com").strip()
    username = os.getenv("BOUWNCE_SYSTEM_USERNAME", "bouwnce").strip()
    full_name = os.getenv("BOUWNCE_SYSTEM_FULL_NAME", "Bouwnce").strip()
    return email, username, full_name


def upgrade() -> None:
    bouwnce_url = (
        "http://res.cloudinary.com/dzjre8izs/image/upload/"
        "v1779746089/chat/65d34fc0-c3b2-4f58-a677-f92ce108b08e/"
        "c1705a6a-127c-483b-9370-41927143a25f.ico"
    )
    bouwnce_public_id = (
        "chat/65d34fc0-c3b2-4f58-a677-f92ce108b08e/c1705a6a-127c-483b-9370-41927143a25f"
    )
    profile_pic = {"url": bouwnce_url, "public_id": bouwnce_public_id}

    email, username, full_name = _bouwnce_identity()

    bind = op.get_bind()
    stmt = sa.text(
        """
        UPDATE users
        SET profile_pic = :profile_pic
        WHERE email = :email OR username = :username OR full_name = :full_name
        """
    ).bindparams(
        sa.bindparam("profile_pic", type_=sa.JSON),
        sa.bindparam("email", type_=sa.String),
        sa.bindparam("username", type_=sa.String),
        sa.bindparam("full_name", type_=sa.String),
    )
    bind.execute(
        stmt,
        {
            "profile_pic": profile_pic,
            "email": email,
            "username": username,
            "full_name": full_name,
        },
    )


def downgrade() -> None:
    email, username, full_name = _bouwnce_identity()
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            UPDATE users
            SET profile_pic = NULL
            WHERE email = :email OR username = :username OR full_name = :full_name
            """
        ),
        {"email": email, "username": username, "full_name": full_name},
    )
