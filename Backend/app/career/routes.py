from flask import Blueprint, abort, render_template, redirect, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models import CareerAssessment
from app.services.career_profile import update_profile

from .engine import recommend_careers
from .forms import CareerAssessmentForm

bp = Blueprint("career", __name__, url_prefix="/career")


@bp.route("/assess", methods=["GET", "POST"])
@login_required
def assess():
    form = CareerAssessmentForm()
    if form.validate_on_submit():
        result = recommend_careers(
            form.skills.data,
            form.interests.data,
            form.cgpa.data,
            form.certifications.data or "",
        )
        top = result["top"]
        assessment = CareerAssessment(
            user_id=current_user.id,
            skills=form.skills.data,
            interests=form.interests.data,
            cgpa=float(form.cgpa.data),
            certifications=form.certifications.data or "",
            recommended_career=top["title"],
            confidence_score=top["match_percentage"],
            explanation=top["explanation"],
            result_json=result,
        )
        db.session.add(assessment)
        update_profile(current_user, learning_track=top["title"], source="assessment")
        db.session.commit()
        return redirect(url_for("career.result", assessment_id=assessment.id))
    return render_template("career/assess.html", form=form)


@bp.get("/history")
@login_required
def history():
    assessments = CareerAssessment.query.filter_by(user_id=current_user.id).order_by(CareerAssessment.created_at.desc()).all()
    return render_template("career/history.html", assessments=assessments)


@bp.get("/result/<int:assessment_id>")
@login_required
def result(assessment_id):
    assessment = db.session.get(CareerAssessment, assessment_id)
    if not assessment or assessment.user_id != current_user.id:
        abort(404)
    return render_template("career/result.html", assessment=assessment, result=assessment.result_json)
