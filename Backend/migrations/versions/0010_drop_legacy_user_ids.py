"""drop obsolete integer user ownership columns

Revision ID: 0010_drop_legacy_user_ids
Revises: 0009_uuid_profiles_storage
Create Date: 2026-07-14
"""

from alembic import op
import sqlalchemy as sa


revision = "0010_drop_legacy_user_ids"
down_revision = "0009_uuid_profiles_storage"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    for table in sa.inspect(bind).get_table_names():
        inspector = sa.inspect(bind)
        if "legacy_user_id" not in {column["name"] for column in inspector.get_columns(table)}:
            continue
        for index in inspector.get_indexes(table):
            if "legacy_user_id" in index["column_names"]:
                op.drop_index(index["name"], table_name=table)
        with op.batch_alter_table(table) as batch_op:
            batch_op.drop_column("legacy_user_id")
        inspector = sa.inspect(bind)
        if "user_id" in {column["name"] for column in inspector.get_columns(table)} and f"ix_{table}_user_id" not in {
            index["name"] for index in inspector.get_indexes(table)
        }:
            op.create_index(f"ix_{table}_user_id", table, ["user_id"])


def downgrade():
    raise RuntimeError("Legacy integer ownership columns cannot be restored safely.")
