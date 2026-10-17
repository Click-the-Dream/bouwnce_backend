"""Expose the event group id directly on outing_events.

Revision ID: 20261016_event_group_id
Revises: 20261016_message_mutations
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261016_event_group_id"
down_revision: str | Sequence[str] | None = "20261016_message_mutations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "outing_events",
        sa.Column("group_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_outing_events_group_id_groups",
        "outing_events",
        "groups",
        ["group_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_unique_constraint(
        "uq_outing_events_group_id", "outing_events", ["group_id"]
    )
    op.execute("""
        UPDATE outing_events
        SET group_id = event_groups.group_id
        FROM event_groups
        WHERE event_groups.event_id = outing_events.id
        """)


def downgrade() -> None:
    op.drop_constraint("uq_outing_events_group_id", "outing_events", type_="unique")
    op.drop_constraint(
        "fk_outing_events_group_id_groups", "outing_events", type_="foreignkey"
    )
    op.drop_column("outing_events", "group_id")
