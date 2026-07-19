"""add career profiles

Revision ID: 0006_career_profiles
Revises: 0005_chat_archive_health
Create Date: 2026-07-11
"""

from alembic import op
import sqlalchemy as sa


revision = "0006_career_profiles"
down_revision = "0005_chat_archive_health"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "career_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("learning_track", sa.String(length=120), nullable=False),
        sa.Column("current_level", sa.String(length=40), nullable=False),
        sa.Column("known_skills", sa.Text(), nullable=False),
        sa.Column("weekly_hours", sa.Integer(), nullable=False),
        sa.Column("target_date", sa.Date(), nullable=True),
        sa.Column("source", sa.String(length=40), nullable=False),
        sa.Column("missing_skills_json", sa.JSON(), nullable=False),
        sa.Column("completed_skills_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index(op.f("ix_career_profiles_user_id"), "career_profiles", ["user_id"], unique=True)
    op.create_index(op.f("ix_career_profiles_learning_track"), "career_profiles", ["learning_track"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_career_profiles_learning_track"), table_name="career_profiles")
    op.drop_index(op.f("ix_career_profiles_user_id"), table_name="career_profiles")
    op.drop_table("career_profiles")
