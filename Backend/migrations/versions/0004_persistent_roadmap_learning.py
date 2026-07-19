"""persistent roadmap and learning resources

Revision ID: 0004_persistent_roadmap_learning
Revises: 0003_chatbot
Create Date: 2026-07-10
"""
from alembic import op
import sqlalchemy as sa


revision = "0004_persistent_roadmap_learning"
down_revision = "0003_chatbot"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "career_roadmaps",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("learning_track", sa.String(length=120), nullable=False),
        sa.Column("current_level", sa.String(length=40), nullable=False),
        sa.Column("known_skills", sa.Text(), nullable=False),
        sa.Column("weekly_hours", sa.Integer(), nullable=False),
        sa.Column("target_date", sa.Date(), nullable=True),
        sa.Column("estimated_weeks", sa.Integer(), nullable=False),
        sa.Column("overall_progress", sa.Integer(), nullable=False),
        sa.Column("generation_method", sa.String(length=40), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_career_roadmaps_is_active"), "career_roadmaps", ["is_active"], unique=False)
    op.create_index(op.f("ix_career_roadmaps_learning_track"), "career_roadmaps", ["learning_track"], unique=False)
    op.create_index(op.f("ix_career_roadmaps_user_id"), "career_roadmaps", ["user_id"], unique=False)
    op.create_table(
        "learning_resources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("skill_name", sa.String(length=120), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("provider", sa.String(length=120), nullable=False),
        sa.Column("resource_type", sa.String(length=60), nullable=False),
        sa.Column("level", sa.String(length=40), nullable=False),
        sa.Column("cost_type", sa.String(length=20), nullable=False),
        sa.Column("priority", sa.String(length=20), nullable=False),
        sa.Column("duration_text", sa.String(length=80), nullable=False),
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_learning_resources_active"), "learning_resources", ["active"], unique=False)
    op.create_index(op.f("ix_learning_resources_cost_type"), "learning_resources", ["cost_type"], unique=False)
    op.create_index(op.f("ix_learning_resources_level"), "learning_resources", ["level"], unique=False)
    op.create_index(op.f("ix_learning_resources_priority"), "learning_resources", ["priority"], unique=False)
    op.create_index(op.f("ix_learning_resources_resource_type"), "learning_resources", ["resource_type"], unique=False)
    op.create_index(op.f("ix_learning_resources_skill_name"), "learning_resources", ["skill_name"], unique=False)
    op.create_table(
        "roadmap_stages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("roadmap_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("level", sa.String(length=40), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("estimated_weeks", sa.Integer(), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("skill_name", sa.String(length=120), nullable=False),
        sa.Column("project", sa.String(length=240), nullable=False),
        sa.Column("assessment_task", sa.String(length=240), nullable=False),
        sa.Column("completion_criteria", sa.Text(), nullable=False),
        sa.Column("resources_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["roadmap_id"], ["career_roadmaps.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_roadmap_stages_roadmap_id"), "roadmap_stages", ["roadmap_id"], unique=False)
    op.create_table(
        "roadmap_tasks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("stage_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=220), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("task_type", sa.String(length=60), nullable=False),
        sa.Column("resource_url", sa.String(length=500), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("completed", sa.Boolean(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["stage_id"], ["roadmap_stages.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_roadmap_tasks_stage_id"), "roadmap_tasks", ["stage_id"], unique=False)
    op.create_table(
        "user_learning_resources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("resource_id", sa.Integer(), nullable=False),
        sa.Column("roadmap_stage_id", sa.Integer(), nullable=True),
        sa.Column("bookmarked", sa.Boolean(), nullable=False),
        sa.Column("started", sa.Boolean(), nullable=False),
        sa.Column("completed", sa.Boolean(), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("last_opened_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["resource_id"], ["learning_resources.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["roadmap_stage_id"], ["roadmap_stages.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_user_learning_resources_resource_id"), "user_learning_resources", ["resource_id"], unique=False)
    op.create_index(op.f("ix_user_learning_resources_user_id"), "user_learning_resources", ["user_id"], unique=False)


def downgrade():
    op.drop_table("user_learning_resources")
    op.drop_table("roadmap_tasks")
    op.drop_table("roadmap_stages")
    op.drop_table("learning_resources")
    op.drop_table("career_roadmaps")
