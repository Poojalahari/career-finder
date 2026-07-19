from datetime import datetime

from app.extensions import db


class ResumeScan(db.Model):
    __tablename__ = "resume_scans"
    __table_args__ = (db.CheckConstraint("status in ('pending','processing','completed','failed')", name="ck_resume_scans_status"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Uuid(as_uuid=False), db.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    original_filename = db.Column(db.String(255), nullable=False)
    storage_path = db.Column(db.String(500), nullable=False, unique=True)
    file_sha256 = db.Column(db.String(64), nullable=False, index=True)
    file_size = db.Column(db.Integer, nullable=False)
    page_count = db.Column(db.Integer, nullable=False)
    job_title = db.Column(db.String(160), nullable=False, default="")
    job_description = db.Column(db.Text, nullable=False, default="")
    overall_score = db.Column(db.Integer)
    matched_keywords = db.Column(db.JSON, nullable=False, default=list)
    missing_keywords = db.Column(db.JSON, nullable=False, default=list)
    section_scores = db.Column(db.JSON, nullable=False, default=dict)
    recommendations = db.Column(db.JSON, nullable=False, default=list)
    analysis_json = db.Column(db.JSON, nullable=False, default=dict)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    status = db.Column(db.String(30), nullable=False, default="pending", index=True)
    error_message = db.Column(db.String(500), nullable=False, default="")

    user = db.relationship("User", back_populates="scans")
