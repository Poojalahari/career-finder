"""add optional profile avatar

Revision ID: 0012_profile_avatar
Revises: 0011_drop_legacy_resume_filename
Create Date: 2026-07-15
"""

from alembic import op
import sqlalchemy as sa


revision = "0012_profile_avatar"
down_revision = "0011_drop_legacy_resume_filename"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    if "avatar_url" not in {column["name"] for column in inspector.get_columns("profiles")}:
        op.add_column("profiles", sa.Column("avatar_url", sa.String(length=500), nullable=True))


def downgrade():
    inspector = sa.inspect(op.get_bind())
    if "avatar_url" in {column["name"] for column in inspector.get_columns("profiles")}:
        op.drop_column("profiles", "avatar_url")
