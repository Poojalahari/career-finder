"""chat archive flag

Revision ID: 0005_chat_archive_health
Revises: 0004_persistent_roadmap_learning
Create Date: 2026-07-10
"""
from alembic import op
import sqlalchemy as sa


revision = "0005_chat_archive_health"
down_revision = "0004_persistent_roadmap_learning"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("chat_conversations", sa.Column("archived", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_index(op.f("ix_chat_conversations_archived"), "chat_conversations", ["archived"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_chat_conversations_archived"), table_name="chat_conversations")
    op.drop_column("chat_conversations", "archived")
