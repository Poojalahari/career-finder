from datetime import datetime, timezone
from uuid import uuid4

from flask_login import UserMixin
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db, login_manager


class User(UserMixin, db.Model):
    __tablename__ = "profiles"
    __table_args__ = (db.CheckConstraint("role in ('super_admin','admin','counsellor','student')", name="ck_profiles_role"),)

    id = db.Column(db.Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    email = db.Column(db.String(255), nullable=False, unique=True, index=True)
    email_verified = db.Column(db.Boolean, default=False, nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    avatar_url = db.Column(db.String(500))
    role = db.Column(db.String(20), default="student", nullable=False, index=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    last_login_at = db.Column(db.DateTime(timezone=True))
    is_active_flag = db.Column("is_active", db.Boolean, default=True, nullable=False, index=True)

    assessments = db.relationship("CareerAssessment", back_populates="user", cascade="all, delete-orphan")
    scans = db.relationship("ResumeScan", back_populates="user", cascade="all, delete-orphan")
    learning_progress = db.relationship("LearningProgress", cascade="all, delete-orphan")
    career_roadmaps = db.relationship("CareerRoadmap", cascade="all, delete-orphan")
    resume_documents = db.relationship("ResumeDocument", cascade="all, delete-orphan")
    interview_sessions = db.relationship("InterviewSession", cascade="all, delete-orphan")
    chat_conversations = db.relationship("ChatConversation", cascade="all, delete-orphan")
    career_profile = db.relationship("CareerProfile", uselist=False, cascade="all, delete-orphan")

    @property
    def is_active(self):
        return self.is_active_flag

@login_manager.user_loader
def load_user(user_id):
    try:
        return db.session.get(User, user_id)
    except (TypeError, ValueError, SQLAlchemyError):
        db.session.rollback()
        return None
