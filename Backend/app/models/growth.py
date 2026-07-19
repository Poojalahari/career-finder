from datetime import datetime

from app.extensions import db


class LearningProgress(db.Model):
    __tablename__ = "learning_progress"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Uuid(as_uuid=False), db.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    area = db.Column(db.String(80), nullable=False, index=True)
    item_key = db.Column(db.String(160), nullable=False)
    title = db.Column(db.String(240), nullable=False)
    progress = db.Column(db.Integer, nullable=False, default=0)
    status = db.Column(db.String(40), nullable=False, default="not_started")
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class CareerProfile(db.Model):
    __tablename__ = "career_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Uuid(as_uuid=False), db.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    learning_track = db.Column(db.String(120), nullable=False, default="Python", index=True)
    current_level = db.Column(db.String(40), nullable=False, default="beginner")
    known_skills = db.Column(db.Text, nullable=False, default="")
    weekly_hours = db.Column(db.Integer, nullable=False, default=8)
    target_date = db.Column(db.Date)
    source = db.Column(db.String(40), nullable=False, default="default")
    missing_skills_json = db.Column(db.JSON, nullable=False, default=list)
    completed_skills_json = db.Column(db.JSON, nullable=False, default=list)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class CareerRoadmap(db.Model):
    __tablename__ = "career_roadmaps"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Uuid(as_uuid=False), db.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    learning_track = db.Column(db.String(120), nullable=False, index=True)
    current_level = db.Column(db.String(40), nullable=False, default="beginner")
    known_skills = db.Column(db.Text, nullable=False, default="")
    weekly_hours = db.Column(db.Integer, nullable=False, default=8)
    target_date = db.Column(db.Date)
    estimated_weeks = db.Column(db.Integer, nullable=False, default=0)
    overall_progress = db.Column(db.Integer, nullable=False, default=0)
    generation_method = db.Column(db.String(40), nullable=False, default="local")
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    stages = db.relationship("RoadmapStage", back_populates="roadmap", cascade="all, delete-orphan")


class RoadmapStage(db.Model):
    __tablename__ = "roadmap_stages"

    id = db.Column(db.Integer, primary_key=True)
    roadmap_id = db.Column(db.Integer, db.ForeignKey("career_roadmaps.id", ondelete="CASCADE"), nullable=False, index=True)
    title = db.Column(db.String(180), nullable=False)
    description = db.Column(db.Text, nullable=False)
    level = db.Column(db.String(40), nullable=False)
    sequence = db.Column(db.Integer, nullable=False)
    estimated_weeks = db.Column(db.Integer, nullable=False)
    progress = db.Column(db.Integer, nullable=False, default=0)
    status = db.Column(db.String(40), nullable=False, default="not_started")
    skill_name = db.Column(db.String(120), nullable=False)
    project = db.Column(db.String(240), nullable=False)
    assessment_task = db.Column(db.String(240), nullable=False)
    completion_criteria = db.Column(db.Text, nullable=False)
    resources_json = db.Column(db.JSON, nullable=False, default=list)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    roadmap = db.relationship("CareerRoadmap", back_populates="stages")
    tasks = db.relationship("RoadmapTask", back_populates="stage", cascade="all, delete-orphan")


class RoadmapTask(db.Model):
    __tablename__ = "roadmap_tasks"

    id = db.Column(db.Integer, primary_key=True)
    stage_id = db.Column(db.Integer, db.ForeignKey("roadmap_stages.id", ondelete="CASCADE"), nullable=False, index=True)
    title = db.Column(db.String(220), nullable=False)
    description = db.Column(db.Text, nullable=False)
    task_type = db.Column(db.String(60), nullable=False)
    resource_url = db.Column(db.String(500), nullable=False, default="")
    sequence = db.Column(db.Integer, nullable=False)
    completed = db.Column(db.Boolean, nullable=False, default=False)
    completed_at = db.Column(db.DateTime)

    stage = db.relationship("RoadmapStage", back_populates="tasks")


class LearningResource(db.Model):
    __tablename__ = "learning_resources"

    id = db.Column(db.Integer, primary_key=True)
    skill_name = db.Column(db.String(120), nullable=False, index=True)
    title = db.Column(db.String(240), nullable=False)
    provider = db.Column(db.String(120), nullable=False)
    resource_type = db.Column(db.String(60), nullable=False, index=True)
    level = db.Column(db.String(40), nullable=False, index=True)
    cost_type = db.Column(db.String(20), nullable=False, index=True)
    priority = db.Column(db.String(20), nullable=False, index=True)
    duration_text = db.Column(db.String(80), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    description = db.Column(db.Text, nullable=False)
    active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class UserLearningResource(db.Model):
    __tablename__ = "user_learning_resources"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Uuid(as_uuid=False), db.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    resource_id = db.Column(db.Integer, db.ForeignKey("learning_resources.id", ondelete="CASCADE"), nullable=False, index=True)
    roadmap_stage_id = db.Column(db.Integer, db.ForeignKey("roadmap_stages.id", ondelete="SET NULL"))
    bookmarked = db.Column(db.Boolean, nullable=False, default=False)
    started = db.Column(db.Boolean, nullable=False, default=False)
    completed = db.Column(db.Boolean, nullable=False, default=False)
    progress = db.Column(db.Integer, nullable=False, default=0)
    last_opened_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    resource = db.relationship("LearningResource")


class ResumeDocument(db.Model):
    __tablename__ = "resume_documents"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Uuid(as_uuid=False), db.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    title = db.Column(db.String(160), nullable=False)
    template = db.Column(db.String(40), nullable=False, default="classic")
    content_json = db.Column(db.JSON, nullable=False)
    ats_score = db.Column(db.Integer, nullable=False, default=0)
    optimization_tips = db.Column(db.JSON, nullable=False, default=list)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class InterviewSession(db.Model):
    __tablename__ = "interview_sessions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Uuid(as_uuid=False), db.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    mode = db.Column(db.String(40), nullable=False, default="prep")
    category = db.Column(db.String(80), nullable=False)
    difficulty = db.Column(db.String(40), nullable=False)
    questions_json = db.Column(db.JSON, nullable=False)
    answers_json = db.Column(db.JSON, nullable=False, default=list)
    technical_score = db.Column(db.Integer, nullable=False, default=0)
    communication_score = db.Column(db.Integer, nullable=False, default=0)
    grammar_score = db.Column(db.Integer, nullable=False, default=0)
    final_report = db.Column(db.Text, nullable=False, default="")
    completed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
