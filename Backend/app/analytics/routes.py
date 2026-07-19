from flask import Blueprint, render_template
from flask_login import current_user, login_required

from app.models import CareerAssessment, InterviewSession, LearningProgress, ResumeScan

bp = Blueprint("analytics", __name__, url_prefix="/analytics")


@bp.get("/")
@login_required
def index():
    scans = ResumeScan.query.filter_by(user_id=current_user.id, status="completed").order_by(ResumeScan.created_at.asc()).all()
    assessments = CareerAssessment.query.filter_by(user_id=current_user.id).order_by(CareerAssessment.created_at.asc()).all()
    interviews = InterviewSession.query.filter_by(user_id=current_user.id).order_by(InterviewSession.created_at.asc()).all()
    progress_rows = LearningProgress.query.filter_by(user_id=current_user.id).all()
    progress_avg = round(sum(row.progress for row in progress_rows) / len(progress_rows)) if progress_rows else 0
    return render_template(
        "analytics/index.html",
        scans=scans,
        assessments=assessments,
        interviews=interviews,
        progress_avg=progress_avg,
        skill_progress=progress_rows[:8],
    )
