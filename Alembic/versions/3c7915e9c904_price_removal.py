"""Price removal

Also reconciles the unique constraints the models expect on orders/suborders
(idempotent_key, reference_token, track_id) that earlier batch table
recreations can silently drop on PostgreSQL 18.

Revision ID: 3c7915e9c904
Revises: 061687c6dc2a
Create Date: 2026-07-21 15:52:05.096109

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3c7915e9c904'
down_revision: Union[str, Sequence[str], None] = '061687c6dc2a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(table_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return inspector.has_table(table_name)


def _column_exists(table_name: str, column_name: str) -> bool:
    if not _table_exists(table_name):
        return False
    inspector = sa.inspect(op.get_bind())
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def _constraint_exists(table_name: str, constraint_name: str) -> bool:
    if not _table_exists(table_name):
        return False
    bind = op.get_bind()
    schema = bind.dialect.default_schema_name
    return (
        bind.execute(
            sa.text(
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
            ),
            {
                "schema": schema,
                "table_name": table_name,
                "constraint_name": constraint_name,
            },
        ).first()
        is not None
    )


def _unique_on_column_exists(table_name: str, column_name: str) -> bool:
    if not _table_exists(table_name):
        return False
    inspector = sa.inspect(op.get_bind())
    for unique in inspector.get_unique_constraints(table_name):
        cols = unique.get("column_names") or []
        if column_name in cols:
            return True
    return False


def upgrade() -> None:
    """Upgrade schema."""
    # Reconcile unique constraints the models expect on orders/suborders.
    # Earlier batch table recreations (e.g. 061687c6dc2a) can silently drop
    # them, so re-assert them here at the end of the chain.
    if _column_exists("orders", "reference_token") and not _unique_on_column_exists(
        "orders", "reference_token"
    ):
        op.create_unique_constraint(
            "orders_reference_token_key", "orders", ["reference_token"]
        )

    if _column_exists("orders", "idempotent_key") and not _unique_on_column_exists(
        "orders", "idempotent_key"
    ):
        op.create_unique_constraint(
            "orders_idempotent_key_key", "orders", ["idempotent_key"]
        )

    if _column_exists("orders", "track_id") and not _unique_on_column_exists(
        "orders", "track_id"
    ):
        op.create_unique_constraint("orders_track_id_key", "orders", ["track_id"])

    if _column_exists("suborders", "track_id") and not _unique_on_column_exists(
        "suborders", "track_id"
    ):
        op.create_unique_constraint(
            "suborders_track_id_key", "suborders", ["track_id"]
        )


def downgrade() -> None:
    """Downgrade schema."""
    # Only drop constraints we created under these exact names; leave any
    # pre-existing unique constraint on the same column untouched.
    if _constraint_exists("orders", "orders_reference_token_key"):
        op.drop_constraint("orders_reference_token_key", "orders", type_="unique")

    if _constraint_exists("orders", "orders_idempotent_key_key"):
        op.drop_constraint("orders_idempotent_key_key", "orders", type_="unique")

    if _constraint_exists("orders", "orders_track_id_key"):
        op.drop_constraint("orders_track_id_key", "orders", type_="unique")

    if _constraint_exists("suborders", "suborders_track_id_key"):
        op.drop_constraint("suborders_track_id_key", "suborders", type_="unique")
