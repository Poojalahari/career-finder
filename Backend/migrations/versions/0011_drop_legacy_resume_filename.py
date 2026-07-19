"""drop obsolete local resume filename

Revision ID: 0011_drop_legacy_resume_filename
Revises: 0010_drop_legacy_user_ids
Create Date: 2026-07-15
"""

from alembic import op
import sqlalchemy as sa


revision = "0011_drop_legacy_resume_filename"
down_revision = "0010_drop_legacy_user_ids"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    if "resume_scans" not in inspector.get_table_names():
        return
    if "stored_filename" in {column["name"] for column in inspector.get_columns("resume_scans")}:
        with op.batch_alter_table("resume_scans") as batch_op:
            batch_op.drop_column("stored_filename")


def downgrade():
    raise RuntimeError("Obsolete local resume filenames cannot be restored safely.")
