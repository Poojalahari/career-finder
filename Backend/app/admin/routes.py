from collections import Counter
from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify, render_template
from flask_login import login_required
from sqlalchemy import func

from app.extensions import db
from app.models import CareerAssessment, ChatConversation, InterviewSession, LearningProgress, ResumeDocument, ResumeScan, User
from app.services.authorization import role_required, roles_required

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.get("/")
@login_required
@roles_required("super_admin", "admin")
def index():
    since = datetime.now(timezone.utc) - timedelta(days=30)
    career_counts = Counter(row.recommended_career for row in CareerAssessment.query.all() if row.recommended_career)
    ats_scores = [row.overall_score for row in ResumeScan.query.filter_by(status="completed").all() if row.overall_score is not None]
    interview_scores = [row.technical_score for row in InterviewSession.query.all() if row.technical_score is not None]
    progress_values = [row.progress for row in LearningProgress.query.all() if row.progress is not None]
    metrics = {
        "total_users": User.query.count(),
        "active_users": User.query.filter(User.last_login_at.is_not(None), User.last_login_at >= since).count(),
        "career_assessments": CareerAssessment.query.count(),
        "resume_scans": ResumeScan.query.count(),
        "resume_documents": ResumeDocument.query.count(),
        "chat_conversations": ChatConversation.query.count(),
        "interviews": InterviewSession.query.count(),
        "avg_ats": round(sum(ats_scores) / len(ats_scores)) if ats_scores else 0,
        "avg_interview": round(sum(interview_scores) / len(interview_scores)) if interview_scores else 0,
        "avg_learning": round(sum(progress_values) / len(progress_values)) if progress_values else 0,
        "popular_careers": career_counts.most_common(8),
        "new_users_30d": User.query.filter(User.created_at >= since).count(),
        "db_tables": len(db.metadata.tables),
    }
    feature_usage = [
        ("Career assessments", metrics["career_assessments"]),
        ("ATS scans", metrics["resume_scans"]),
        ("Resume builder", metrics["resume_documents"]),
        ("Chatbot conversations", metrics["chat_conversations"]),
        ("Interview sessions", metrics["interviews"]),
    ]
    taxonomy_count = CareerAssessment.query.with_entities(func.count(func.distinct(CareerAssessment.recommended_career))).scalar() or 0
    return render_template("admin/index.html", metrics=metrics, feature_usage=feature_usage, taxonomy_count=taxonomy_count)


@bp.get("/system")
@login_required
@role_required("super_admin")
def system():
    return jsonify({"status": "ok", "database_tables": len(db.metadata.tables)})
