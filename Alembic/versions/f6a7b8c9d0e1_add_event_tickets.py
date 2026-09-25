"""add event tickets table

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f6a7b8c9d0e1"
down_revision: str | Sequence[str] | None = "e5f6a7b8c9d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Per-ticket-type capacity lives in ``outing_events.ticket_info`` JSONB
    # (optional ``capacity`` key per entry); availability is derived by
    # counting issued event_tickets rows per type — no event-wide columns.

    # One row per purchased ticket unit (not a quantity field): Phase 3/4 need
    # to look up and verify individual tickets by individual codes.
    op.create_table(
        "event_tickets",
        sa.Column("attendance_id", sa.UUID(), nullable=False),
        sa.Column("event_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("ticket_name", sa.String(), nullable=False),
        sa.Column("code", sa.String(length=10), nullable=False),
        sa.Column("unit_amount", sa.Float(), nullable=False),
        sa.Column("qr_code_url", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="valid"),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("used_by", sa.UUID(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["attendance_id"], ["user_event_attendance.id"]),
        sa.ForeignKeyConstraint(["event_id"], ["outing_events.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["used_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    # Global uniqueness of the 10-digit code is the verify-by-code anchor.
    op.create_index(
        "ix_event_tickets_code", "event_tickets", ["code"], unique=True
    )
    op.create_index(
        "ix_event_tickets_attendance_id", "event_tickets", ["attendance_id"]
    )
    op.create_index("ix_event_tickets_event_id", "event_tickets", ["event_id"])


def downgrade() -> None:
    op.drop_index("ix_event_tickets_event_id", table_name="event_tickets")
    op.drop_index("ix_event_tickets_attendance_id", table_name="event_tickets")
    op.drop_index("ix_event_tickets_code", table_name="event_tickets")
    op.drop_table("event_tickets")
