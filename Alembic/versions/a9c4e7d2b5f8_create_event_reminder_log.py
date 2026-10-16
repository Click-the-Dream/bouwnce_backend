"""create event_reminder_log table

Revision ID: a9c4e7d2b5f8
Revises: f6a7b8c9d0e1
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a9c4e7d2b5f8"
down_revision: str | Sequence[str] | None = "f6a7b8c9d0e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Dedup anchor for the scheduled event-reminder job: one row per
    # (attendance, event, reminder window). The unique constraint backs the
    # INSERT ... ON CONFLICT DO NOTHING claim in
    # EventReminderLog.claim_windows, so concurrent worker runs can never
    # double-send a reminder window.
    op.create_table(
        "event_reminder_log",
        sa.Column("event_id", sa.UUID(), nullable=False),
        sa.Column("attendance_id", sa.UUID(), nullable=False),
        sa.Column("window", sa.Integer(), nullable=False),
        sa.Column("is_sent", sa.Boolean(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["outing_events.id"]),
        sa.ForeignKeyConstraint(["attendance_id"], ["user_event_attendance.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "attendance_id",
            "event_id",
            "window",
            name="uq_event_reminder_log_attendance_event_window",
        ),
    )
    op.create_index(
        "ix_event_reminder_log_event_id", "event_reminder_log", ["event_id"]
    )
    op.create_index(
        "ix_event_reminder_log_attendance_id", "event_reminder_log", ["attendance_id"]
    )


def downgrade() -> None:
    op.drop_index(
        "ix_event_reminder_log_attendance_id", table_name="event_reminder_log"
    )
    op.drop_index("ix_event_reminder_log_event_id", table_name="event_reminder_log")
    op.drop_table("event_reminder_log")
