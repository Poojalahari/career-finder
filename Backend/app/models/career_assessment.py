from datetime import datetime

from app.extensions import db


class CareerAssessment(db.Model):
    __tablename__ = "career_assessments"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Uuid(as_uuid=False), db.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    skills = db.Column(db.Text, nullable=False)
    interests = db.Column(db.Text, nullable=False)
    cgpa = db.Column(db.Float, nullable=False)
    certifications = db.Column(db.Text, nullable=False, default="")
    recommended_career = db.Column(db.String(120), nullable=False)
    confidence_score = db.Column(db.Integer, nullable=False)
    explanation = db.Column(db.Text, nullable=False)
    result_json = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    user = db.relationship("User", back_populates="assessments")
