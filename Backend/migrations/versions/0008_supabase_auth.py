"""link application users to Supabase Auth

Revision ID: 0008_supabase_auth
Revises: 0007_learning_track_names
Create Date: 2026-07-12
"""

from alembic import op
import sqlalchemy as sa


revision = "0008_supabase_auth"
down_revision = "0007_learning_track_names"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("password_hash", existing_type=sa.String(length=255), nullable=True)
        batch_op.add_column(sa.Column("supabase_user_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.create_index("ix_users_supabase_user_id", ["supabase_user_id"], unique=True)


def downgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_index("ix_users_supabase_user_id")
        batch_op.drop_column("email_verified")
        batch_op.drop_column("supabase_user_id")
        batch_op.alter_column("password_hash", existing_type=sa.String(length=255), nullable=False)
