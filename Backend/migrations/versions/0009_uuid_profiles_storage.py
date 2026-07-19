"""UUID profiles, user ownership, and Supabase storage paths

Revision ID: 0009_uuid_profiles_storage
Revises: 0008_supabase_auth
Create Date: 2026-07-14
"""

from datetime import datetime, timezone
from uuid import NAMESPACE_URL, uuid5

from alembic import op
import sqlalchemy as sa


revision = "0009_uuid_profiles_storage"
down_revision = "0008_supabase_auth"
branch_labels = None
depends_on = None

USER_TABLES = (
    "career_assessments",
    "resume_scans",
    "learning_progress",
    "career_profiles",
    "career_roadmaps",
    "user_learning_resources",
    "resume_documents",
    "interview_sessions",
    "chat_conversations",
)


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    uuid_type = sa.Uuid(as_uuid=False)

    if "profiles" not in tables:
        op.create_table(
            "profiles",
            sa.Column("id", uuid_type, primary_key=True),
            sa.Column("email", sa.String(255), nullable=False, unique=True),
            sa.Column("full_name", sa.String(120), nullable=False),
            sa.Column("avatar_url", sa.String(500)),
            sa.Column("role", sa.String(20), nullable=False, server_default="student"),
            sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("last_login_at", sa.DateTime(timezone=True)),
            sa.CheckConstraint("role in ('super_admin','admin','counsellor','student')", name="ck_profiles_role"),
        )
        op.create_index("ix_profiles_email", "profiles", ["email"])
        op.create_index("ix_profiles_role", "profiles", ["role"])
        op.create_index("ix_profiles_is_active", "profiles", ["is_active"])
        op.create_index("ix_profiles_created_at", "profiles", ["created_at"])

    user_map = {}
    if "users" in tables:
        users = bind.execute(sa.text("select id, email, full_name, supabase_user_id, email_verified, created_at, updated_at, last_login_at, is_active_flag from users")).mappings()
        for row in users:
            profile_id = row["supabase_user_id"] or str(uuid5(NAMESPACE_URL, f"careerpath:{row['id']}:{row['email']}"))
            user_map[row["id"]] = profile_id
            exists = bind.execute(sa.text("select 1 from profiles where id = :id"), {"id": profile_id}).first()
            if not exists:
                now = datetime.now(timezone.utc)
                bind.execute(
                    sa.text("insert into profiles (id,email,full_name,role,email_verified,is_active,created_at,updated_at,last_login_at) values (:id,:email,:name,'student',:verified,:active,:created,:updated,:last_login)"),
                    {
                        "id": profile_id,
                        "email": row["email"],
                        "name": row["full_name"],
                        "verified": bool(row["email_verified"]),
                        "active": bool(row["is_active_flag"]),
                        "created": row["created_at"] or now,
                        "updated": row["updated_at"] or now,
                        "last_login": row["last_login_at"],
                    },
                )

    for table in USER_TABLES:
        if table not in tables:
            continue
        columns = {column["name"] for column in sa.inspect(bind).get_columns(table)}
        if "legacy_user_id" in columns:
            continue
        op.add_column(table, sa.Column("profile_id", uuid_type, nullable=True))
        rows = bind.execute(sa.text(f"select id, user_id from {table}")).mappings()
        for row in rows:
            profile_id = user_map.get(row["user_id"])
            if profile_id:
                bind.execute(sa.text(f"update {table} set profile_id = :profile_id where id = :id"), {"profile_id": profile_id, "id": row["id"]})
        index_name = f"ix_{table}_user_id"
        indexes = {index["name"] for index in sa.inspect(bind).get_indexes(table)}
        with op.batch_alter_table(table) as batch_op:
            if index_name in indexes:
                batch_op.drop_index(index_name)
            batch_op.alter_column("user_id", new_column_name="legacy_user_id", existing_type=sa.Integer(), nullable=False)
            batch_op.alter_column("profile_id", new_column_name="user_id", existing_type=uuid_type, nullable=False)
            batch_op.create_foreign_key(f"fk_{table}_profile", "profiles", ["user_id"], ["id"], ondelete="CASCADE")
            batch_op.create_index(index_name, ["user_id"])

    resume_columns = {column["name"] for column in sa.inspect(bind).get_columns("resume_scans")}
    if "storage_path" not in resume_columns:
        op.add_column("resume_scans", sa.Column("storage_path", sa.String(500), nullable=True))
        bind.execute(sa.text("update resume_scans set storage_path = stored_filename where storage_path is null"))
        with op.batch_alter_table("resume_scans") as batch_op:
            batch_op.alter_column("storage_path", existing_type=sa.String(500), nullable=False)
            batch_op.alter_column("overall_score", existing_type=sa.Integer(), nullable=True)
            batch_op.create_unique_constraint("uq_resume_scans_storage_path", ["storage_path"])
            batch_op.create_check_constraint("ck_resume_scans_status", "status in ('pending','processing','completed','failed')")
        if "ix_resume_scans_status" not in {index["name"] for index in sa.inspect(bind).get_indexes("resume_scans")}:
            op.create_index("ix_resume_scans_status", "resume_scans", ["status"])

    if "users" in tables and "password_hash" in {column["name"] for column in sa.inspect(bind).get_columns("users")}:
        with op.batch_alter_table("users") as batch_op:
            batch_op.drop_column("password_hash")


def downgrade():
    raise RuntimeError("UUID ownership migration is intentionally irreversible; restore from a database backup.")
