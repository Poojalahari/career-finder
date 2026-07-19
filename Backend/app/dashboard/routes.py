from flask import Blueprint, flash, redirect, render_template, session, url_for
from flask_login import current_user, login_required, logout_user
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import CareerAssessment, InterviewSession, ResumeDocument, ResumeScan, User
from app.services.career_profile import get_or_create_profile
from app.services.file_storage import StorageError, delete_resume
from app.services.security import normalize_email
from app.services import supabase_auth

from .forms import DeleteAccountForm, PasswordChangeForm, ProfileForm

bp = Blueprint("dashboard", __name__)


@bp.get("/dashboard")
@login_required
def index():
    scans = (
        ResumeScan.query.filter_by(user_id=current_user.id, status="completed")
        .order_by(ResumeScan.created_at.desc())
        .limit(5)
        .all()
    )
    assessments = (
        CareerAssessment.query.filter_by(user_id=current_user.id)
        .order_by(CareerAssessment.created_at.desc())
        .limit(5)
        .all()
    )
    all_scores = [scan.overall_score for scan in current_user.scans if scan.status == "completed" and scan.overall_score is not None]
    profile = get_or_create_profile(current_user)
    stats = {
        "scan_count": len(current_user.scans),
        "avg_score": round(sum(all_scores) / len(all_scores)) if all_scores else 0,
        "best_score": max(all_scores) if all_scores else 0,
        "assessment_count": len(current_user.assessments),
        "latest_career": profile.learning_track,
        "resume_count": ResumeDocument.query.filter_by(user_id=current_user.id).count(),
        "interview_count": InterviewSession.query.filter_by(user_id=current_user.id).count(),
    }
    return render_template("dashboard/index.html", stats=stats, scans=scans, assessments=assessments)


@bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    profile_form = ProfileForm(obj=current_user)
    password_form = PasswordChangeForm()
    delete_form = DeleteAccountForm()
    if profile_form.submit.data and profile_form.validate_on_submit():
        email = normalize_email(profile_form.email.data)
        duplicate = User.query.filter(User.email == email, User.id != current_user.id).first()
        if duplicate:
            flash("That email is already in use.", "error")
        else:
            try:
                if supabase_auth.enabled() and email != current_user.email:
                    supabase_auth.update_email(session.get("supabase_access_token", ""), email)
                    flash("Confirm the new address from the verification email.", "info")
                current_user.full_name = profile_form.full_name.data.strip()
                if not supabase_auth.enabled():
                    current_user.email = email
                db.session.commit()
                flash("Profile updated.", "success")
            except (IntegrityError, supabase_auth.SupabaseAuthError) as exc:
                db.session.rollback()
                flash(str(exc) if isinstance(exc, supabase_auth.SupabaseAuthError) else "That email is already in use.", "error")
        return redirect(url_for("dashboard.profile"))
    if password_form.submit.data and password_form.validate_on_submit():
        try:
            auth_session = supabase_auth.sign_in(current_user.email, password_form.current_password.data)
            supabase_auth.update_password(auth_session.access_token, password_form.new_password.data)
            flash("Password changed.", "success")
        except supabase_auth.SupabaseAuthError:
            flash("Current password is incorrect or the authentication service is unavailable.", "error")
        return redirect(url_for("dashboard.profile"))
    if delete_form.submit.data and delete_form.validate_on_submit():
        if delete_form.confirmation.data != "DELETE":
            flash("Type DELETE to confirm account deletion.", "error")
            return redirect(url_for("dashboard.profile"))
        try:
            supabase_auth.sign_in(current_user.email, delete_form.password.data)
            for scan in current_user.scans:
                if scan.status == "completed":
                    delete_resume(scan.storage_path, session.get("supabase_access_token", ""))
            user_id = current_user.id
            db.session.delete(current_user)
            db.session.flush()
            supabase_auth.delete_user(user_id)
            db.session.commit()
        except (supabase_auth.SupabaseAuthError, StorageError, IntegrityError):
            db.session.rollback()
            flash("Current password is incorrect or account deletion is unavailable.", "error")
            return redirect(url_for("dashboard.profile"))
        logout_user()
        session.clear()
        flash("Account deleted.", "info")
        return redirect(url_for("auth.register"))
    return render_template("dashboard/profile.html", profile_form=profile_form, password_form=password_form, delete_form=delete_form)


@bp.get("/privacy")
@login_required
def privacy():
    return render_template("dashboard/privacy.html")
