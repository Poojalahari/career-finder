from uuid import uuid4

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, send_file, session, url_for
from flask_login import current_user, login_required
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models import ResumeScan
from app.services.file_storage import StorageError, UploadValidationError, delete_resume, signed_resume_url, upload_resume, validate_pdf_upload

from .forms import ResumeScanForm
from .parser import extract_pdf_text
from .report_service import generate_report
from .scorer import score_resume

bp = Blueprint("ats", __name__, url_prefix="/ats")


@bp.route("/scan", methods=["GET", "POST"])
@login_required
def scan():
    form = ResumeScanForm()
    if request.method == "POST" and len(request.files.getlist("resume")) != 1:
        form.resume.errors = ("Upload exactly one PDF.",)
    elif form.validate_on_submit():
        scan_obj = None
        uploaded = False
        storage_path = f"{current_user.id}/resumes/{uuid4().hex}.pdf"
        try:
            original, data, sha256 = validate_pdf_upload(form.resume.data)
            scan_obj = ResumeScan(
                user_id=current_user.id,
                original_filename=original,
                storage_path=storage_path,
                file_sha256=sha256,
                file_size=len(data),
                page_count=0,
                job_title=form.job_title.data or "",
                job_description=form.job_description.data or "",
                status="processing",
            )
            db.session.add(scan_obj)
            db.session.commit()

            text, page_count = extract_pdf_text(data, current_app.config.get("MAX_PDF_PAGES", 10))
            result = score_resume(text, page_count, form.job_description.data or "")
            upload_resume(storage_path, data, session.get("supabase_access_token", ""))
            uploaded = True
            scan_obj.page_count = page_count
            scan_obj.overall_score = result["overall_score"]
            scan_obj.matched_keywords = result["matched_keywords"]
            scan_obj.missing_keywords = result["missing_keywords"]
            scan_obj.section_scores = result["section_scores"]
            scan_obj.recommendations = result["recommendations"]
            scan_obj.analysis_json = result
            scan_obj.status = "completed"
            db.session.commit()
            return redirect(url_for("ats.result", scan_id=scan_obj.id))
        except UploadValidationError as exc:
            db.session.rollback()
            _mark_failed(scan_obj)
            flash(str(exc), "error")
        except (StorageError, SQLAlchemyError):
            db.session.rollback()
            if uploaded:
                _cleanup_uploaded_object(storage_path)
            _mark_failed(scan_obj)
            current_app.logger.exception("Resume scan persistence failed")
            flash("The resume could not be stored safely.", "error")
        except Exception:
            db.session.rollback()
            if uploaded:
                _cleanup_uploaded_object(storage_path)
            _mark_failed(scan_obj)
            current_app.logger.exception("Resume scan failed")
            flash("The resume could not be analyzed safely.", "error")
    return render_template("ats/scan.html", form=form)


def _mark_failed(scan_obj):
    if not scan_obj or not scan_obj.id:
        return
    try:
        failed = db.session.get(ResumeScan, scan_obj.id)
        if failed:
            failed.status = "failed"
            failed.error_message = "Processing failed safely."
            db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Could not mark resume scan as failed")


def _cleanup_uploaded_object(storage_path):
    try:
        delete_resume(storage_path, session.get("supabase_access_token", ""))
    except StorageError:
        current_app.logger.exception("Could not clean up uploaded resume object")


@bp.get("/history")
@login_required
def history():
    scans = ResumeScan.query.filter_by(user_id=current_user.id).order_by(ResumeScan.created_at.desc()).all()
    return render_template("ats/history.html", scans=scans)


@bp.get("/result/<int:scan_id>")
@login_required
def result(scan_id):
    scan_obj = owned_scan(scan_id)
    if scan_obj.status != "completed":
        abort(404)
    return render_template("ats/result.html", scan=scan_obj, analysis=scan_obj.analysis_json)


@bp.get("/resume/<int:scan_id>")
@login_required
def resume(scan_id):
    scan_obj = owned_scan(scan_id)
    if scan_obj.status != "completed":
        abort(404)
    try:
        return redirect(signed_resume_url(scan_obj.storage_path, session.get("supabase_access_token", "")))
    except StorageError:
        flash("A secure resume link could not be created.", "error")
        return redirect(url_for("ats.history"))


@bp.get("/report/<int:scan_id>")
@login_required
def report(scan_id):
    scan_obj = owned_scan(scan_id)
    if scan_obj.status != "completed":
        abort(404)
    return send_file(generate_report(scan_obj), mimetype="application/pdf", as_attachment=True, download_name=f"ats-report-{scan_obj.id}.pdf")


@bp.post("/delete/<int:scan_id>")
@login_required
def delete(scan_id):
    scan_obj = owned_scan(scan_id)
    try:
        if scan_obj.status == "completed":
            delete_resume(scan_obj.storage_path, session.get("supabase_access_token", ""))
        db.session.delete(scan_obj)
        db.session.commit()
    except (StorageError, SQLAlchemyError):
        db.session.rollback()
        current_app.logger.exception("Resume scan deletion failed")
        flash("The scan could not be deleted safely.", "error")
        return redirect(url_for("ats.history"))
    flash("Scan and stored resume deleted.", "success")
    return redirect(url_for("ats.history"))


def owned_scan(scan_id):
    scan_obj = db.session.get(ResumeScan, scan_id)
    if not scan_obj or scan_obj.user_id != current_user.id:
        abort(404)
    return scan_obj
