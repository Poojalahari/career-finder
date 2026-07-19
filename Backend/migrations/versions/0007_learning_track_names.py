"""rename growth target fields to learning track

Revision ID: 0007_learning_track_names
Revises: 0006_career_profiles
Create Date: 2026-07-12
"""

from alembic import op
import sqlalchemy as sa


revision = "0007_learning_track_names"
down_revision = "0006_career_profiles"
branch_labels = None
depends_on = None


def _has_column(inspector, table_name, column_name):
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def _has_index(inspector, table_name, index_name):
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    old_name = "target_" + "career"
    if "career_roadmaps" in inspector.get_table_names():
        if _has_index(inspector, "career_roadmaps", "ix_career_roadmaps_" + old_name):
            op.drop_index("ix_career_roadmaps_" + old_name, table_name="career_roadmaps")
        if _has_column(inspector, "career_roadmaps", old_name) and not _has_column(inspector, "career_roadmaps", "learning_track"):
            op.alter_column("career_roadmaps", old_name, new_column_name="learning_track", existing_type=sa.String(length=120), existing_nullable=False)
        if not _has_index(sa.inspect(bind), "career_roadmaps", "ix_career_roadmaps_learning_track"):
            op.create_index("ix_career_roadmaps_learning_track", "career_roadmaps", ["learning_track"])
    inspector = sa.inspect(bind)
    if "career_profiles" in inspector.get_table_names():
        if _has_index(inspector, "career_profiles", "ix_career_profiles_" + old_name):
            op.drop_index("ix_career_profiles_" + old_name, table_name="career_profiles")
        if _has_column(inspector, "career_profiles", old_name) and not _has_column(inspector, "career_profiles", "learning_track"):
            op.alter_column("career_profiles", old_name, new_column_name="learning_track", existing_type=sa.String(length=120), existing_nullable=False)
        if not _has_index(sa.inspect(bind), "career_profiles", "ix_career_profiles_learning_track"):
            op.create_index("ix_career_profiles_learning_track", "career_profiles", ["learning_track"])


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    old_name = "target_" + "career"
    if "career_roadmaps" in inspector.get_table_names():
        if _has_index(inspector, "career_roadmaps", "ix_career_roadmaps_learning_track"):
            op.drop_index("ix_career_roadmaps_learning_track", table_name="career_roadmaps")
        if _has_column(inspector, "career_roadmaps", "learning_track") and not _has_column(inspector, "career_roadmaps", old_name):
            op.alter_column("career_roadmaps", "learning_track", new_column_name=old_name, existing_type=sa.String(length=120), existing_nullable=False)
        op.create_index("ix_career_roadmaps_" + old_name, "career_roadmaps", [old_name])
    inspector = sa.inspect(bind)
    if "career_profiles" in inspector.get_table_names():
        if _has_index(inspector, "career_profiles", "ix_career_profiles_learning_track"):
            op.drop_index("ix_career_profiles_learning_track", table_name="career_profiles")
        if _has_column(inspector, "career_profiles", "learning_track") and not _has_column(inspector, "career_profiles", old_name):
            op.alter_column("career_profiles", "learning_track", new_column_name=old_name, existing_type=sa.String(length=120), existing_nullable=False)
        op.create_index("ix_career_profiles_" + old_name, "career_profiles", [old_name])
