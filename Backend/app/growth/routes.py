from datetime import datetime
from urllib.parse import urlparse

from flask import Blueprint, abort, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_

from app.extensions import db
from app.models import (
    CareerRoadmap,
    InterviewSession,
    LearningResource,
    ResumeDocument,
    RoadmapStage,
    RoadmapTask,
    UserLearningResource,
)
from app.services.career_profile import get_or_create_profile, update_profile

from .forms import InterviewSetupForm, ResumeBuilderForm, RoadmapForm
from .services import (
    build_questions,
    build_roadmap,
    completed_skill_names,
    evaluate_answers,
    get_available_tracks,
    get_career_skills,
    get_coding_platforms,
    learning_resource_rows_for_plan,
    RESOURCE_CATALOG,
    resume_pdf,
    score_resume_document,
)

bp = Blueprint("growth", __name__, url_prefix="/growth")


def latest_career():
    return get_or_create_profile(current_user).learning_track


def language_choices():
    return [(track, track) for track in get_available_tracks()]


@bp.route("/roadmap", methods=["GET", "POST"])
@login_required
def roadmap():
    active = CareerRoadmap.query.filter_by(user_id=current_user.id, is_active=True).order_by(CareerRoadmap.updated_at.desc()).first()
    profile = get_or_create_profile(current_user)
    requested_language = request.args.get("language")
    initial_language = requested_language if requested_language in get_available_tracks() else profile.learning_track
    form = RoadmapForm(
        learning_track=initial_language,
        known_skills=profile.known_skills,
        current_level=profile.current_level,
        weekly_hours=profile.weekly_hours,
        target_date=profile.target_date,
    )
    form.learning_track.choices = language_choices()
    if profile.learning_track not in get_available_tracks():
        form.learning_track.data = "Python"
    if form.validate_on_submit():
        profile = update_profile(
            current_user,
            learning_track=form.learning_track.data,
            known_skills=form.known_skills.data or "",
            current_level=form.current_level.data,
            weekly_hours=form.weekly_hours.data,
            target_date=form.target_date.data,
            source="roadmap",
        )
        completed = completed_skill_names(CareerRoadmap.query.filter_by(user_id=current_user.id).all())
        if active:
            active.is_active = False
        plan = build_roadmap(profile.learning_track, profile.known_skills, profile.current_level, profile.weekly_hours, [], completed, profile.target_date)
        profile.missing_skills_json = plan["missing_skills"]
        roadmap_obj = CareerRoadmap(
            user_id=current_user.id,
            learning_track=profile.learning_track,
            current_level=profile.current_level,
            known_skills=profile.known_skills,
            weekly_hours=profile.weekly_hours,
            target_date=profile.target_date,
            estimated_weeks=plan["estimated_weeks"],
            generation_method="local",
        )
        db.session.add(roadmap_obj)
        db.session.flush()
        for sequence, phase in enumerate(plan["phases"], start=1):
            phase["date_warning"] = plan.get("date_warning")
            stage = RoadmapStage(
                roadmap_id=roadmap_obj.id,
                title=phase["title"],
                skill_name=phase["title"],
                description=phase["description"],
                level=phase["level"],
                sequence=sequence,
                estimated_weeks=phase["weeks"],
                progress=phase["progress"],
                status="completed" if phase["progress"] == 100 else "in_progress" if phase["progress"] else "not_started",
                project=phase["projects"][0],
                assessment_task=phase["assessment"],
                completion_criteria=phase["criteria"],
                resources_json=phase,
            )
            db.session.add(stage)
            db.session.flush()
            task_rows = phase.get("tasks") or [
                {
                    "title": skill["name"],
                    "description": f"Complete and document: {skill['name']}",
                    "type": "lesson",
                    "resource_url": phase["resources"][0]["url"] if phase["resources"] else "",
                    "completed": status == "Completed",
                }
                for skill, status in zip(phase["skills"], phase["statuses"])
            ]
            for task_sequence, task_data in enumerate(task_rows, start=1):
                db.session.add(
                    RoadmapTask(
                        stage_id=stage.id,
                        title=task_data["title"],
                        description=task_data["description"],
                        task_type=task_data["type"],
                        resource_url=task_data["resource_url"],
                        sequence=task_sequence,
                        completed=task_data["completed"],
                        completed_at=datetime.utcnow() if task_data["completed"] else None,
                    )
                )
        seed_learning_resources(plan)
        recalculate_roadmap(roadmap_obj)
        update_profile(current_user, source="roadmap")
        db.session.commit()
        flash("Roadmap generated and previous roadmap archived.", "success")
        return redirect(url_for("growth.roadmap"))
    history = CareerRoadmap.query.filter_by(user_id=current_user.id).order_by(CareerRoadmap.updated_at.desc()).all()
    return render_template("growth/roadmap.html", form=form, roadmap=active, history=history, profile=profile)


@bp.post("/progress")
@login_required
def update_progress():
    stage_id = request.form.get("stage_id")
    task_id = request.form.get("task_id")
    value = max(0, min(100, int(request.form.get("progress", "0"))))
    if task_id:
        task = db.session.get(RoadmapTask, int(task_id))
        if not task or task.stage.roadmap.user_id != current_user.id:
            abort(404)
        task.completed = request.form.get("completed") == "on"
        task.completed_at = datetime.utcnow() if task.completed else None
        recalculate_stage(task.stage)
    elif stage_id:
        stage = db.session.get(RoadmapStage, int(stage_id))
        if not stage or stage.roadmap.user_id != current_user.id:
            abort(404)
        stage.progress = value
        stage.status = "completed" if value == 100 else "in_progress" if value else "not_started"
        recalculate_roadmap(stage.roadmap)
    else:
        abort(400)
    db.session.commit()
    flash("Progress updated.", "success")
    return redirect(request.referrer or url_for("growth.roadmap"))


@bp.get("/learning")
@login_required
def learning():
    profile = get_or_create_profile(current_user)
    seed_learning_resources()
    selected_track = request.args.get("language") or request.args.get("track") or profile.learning_track
    if selected_track not in get_available_tracks():
        selected_track = ""
    approved_skills = [track.lower() for track in get_available_tracks()]
    query = LearningResource.query.filter_by(active=True).filter(LearningResource.skill_name.in_(approved_skills))
    if selected_track:
        query = query.filter(LearningResource.skill_name == selected_track.lower())
    search = request.args.get("q")
    if search:
        query = query.filter(
            or_(
                LearningResource.title.ilike(f"%{search}%"),
                LearningResource.provider.ilike(f"%{search}%"),
                LearningResource.skill_name.ilike(f"%{search}%"),
                LearningResource.description.ilike(f"%{search}%"),
            )
        )
    query = query.order_by(LearningResource.skill_name.asc())
    resources = query.all()
    states = {row.resource_id: row for row in UserLearningResource.query.filter_by(user_id=current_user.id).all()}
    completed_topics = completed_skill_names(CareerRoadmap.query.filter_by(user_id=current_user.id).all())
    platform_cards = get_coding_platforms(selected_track, search)
    language_cards = []
    for resource in resources:
        language = next((track for track in get_available_tracks() if track.lower() == resource.skill_name), resource.skill_name.title())
        topics = [skill["name"] for skill in get_career_skills(language)]
        state = states.get(resource.id)
        lesson_keys = {topic.lower() for topic in topics}
        completed_count = sum(1 for topic in lesson_keys if topic in completed_topics)
        progress = round(completed_count / max(len(topics), 1) * 100)
        if state and state.completed:
            progress = 100
        language_cards.append(
            {
                "resource": resource,
                "language": language,
                "description": resource.description,
                "topics": topics,
                "completed_count": completed_count,
                "total_count": len(topics),
                "progress": progress,
                "status": "Completed" if progress == 100 else "In progress" if progress else "Not started",
                "state": state,
            }
        )
    filter_options = {
        "languages": get_available_tracks(),
    }
    active_filters = [
        (label, request.args.get(key))
        for label, key in [("Search", "q"), ("Language", "language")]
        if request.args.get(key)
    ]
    return render_template(
        "growth/learning.html",
        learning_track=selected_track,
        resources=resources,
        language_cards=language_cards,
        platform_cards=platform_cards,
        platform_count=len(platform_cards),
        states=states,
        filter_options=filter_options,
        active_filters=active_filters,
        result_count=len(language_cards),
        profile=profile,
    )


@bp.post("/learning/<int:resource_id>/<action>")
@login_required
def learning_action(resource_id, action):
    resource_obj = db.session.get(LearningResource, resource_id)
    if not resource_obj or not resource_obj.active:
        abort(404)
    state = UserLearningResource.query.filter_by(user_id=current_user.id, resource_id=resource_id).first()
    if not state:
        state = UserLearningResource(user_id=current_user.id, resource_id=resource_id)
        db.session.add(state)
    if action == "bookmark":
        state.bookmarked = True
    elif action == "unbookmark":
        state.bookmarked = False
    elif action == "start":
        state.started = True
        state.last_opened_at = datetime.utcnow()
    elif action == "progress":
        state.started = True
        state.progress = max(0, min(100, int(request.form.get("progress", "0"))))
        state.completed = state.progress == 100
    elif action == "complete":
        state.started = True
        state.completed = True
        state.progress = 100
    elif action == "open":
        state.last_opened_at = datetime.utcnow()
    else:
        abort(400)
    db.session.commit()
    flash("Learning resource updated.", "success")
    return redirect(request.referrer or url_for("growth.learning"))


@bp.route("/resume-builder", methods=["GET", "POST"])
@login_required
def resume_builder():
    form = ResumeBuilderForm()
    documents = ResumeDocument.query.filter_by(user_id=current_user.id).order_by(ResumeDocument.updated_at.desc()).all()
    preview = None
    if form.validate_on_submit():
        content = {
            "name": form.name.data,
            "email": form.email.data,
            "phone": form.phone.data or "",
            "links": form.links.data or "",
            "summary": form.summary.data,
            "skills": form.skills.data,
            "experience": form.experience.data,
            "projects": form.projects.data or "",
            "education": form.education.data,
        }
        score, tips = score_resume_document(content)
        document = ResumeDocument(
            user_id=current_user.id,
            title=form.title.data,
            template=form.template.data,
            content_json=content,
            ats_score=score,
            optimization_tips=tips,
        )
        db.session.add(document)
        db.session.commit()
        flash("Resume saved and scored.", "success")
        return redirect(url_for("growth.resume_preview", document_id=document.id))
    return render_template("growth/resume_builder.html", form=form, documents=documents, preview=preview)


@bp.get("/resume-builder/<int:document_id>")
@login_required
def resume_preview(document_id):
    document = owned_resume(document_id)
    return render_template("growth/resume_preview.html", document=document)


@bp.get("/resume-builder/<int:document_id>/download")
@login_required
def resume_download(document_id):
    document = owned_resume(document_id)
    return send_file(resume_pdf(document), mimetype="application/pdf", as_attachment=True, download_name=f"{document.title}.pdf")


@bp.route("/interview-prep", methods=["GET", "POST"])
@login_required
def interview_prep():
    mode = request.form.get("mode") or request.args.get("mode", "prep")
    if mode not in {"prep", "mock"}:
        mode = "prep"
    return interview_setup(mode)


@bp.route("/mock-interview", methods=["GET", "POST"])
@login_required
def mock_interview():
    if request.method == "POST":
        return interview_setup("mock")
    return redirect(url_for("growth.interview_prep", mode="mock"), code=302)


def interview_setup(mode):
    form = InterviewSetupForm()
    sessions = (
        InterviewSession.query.filter_by(user_id=current_user.id)
        .order_by(InterviewSession.created_at.desc())
        .limit(5)
        .all()
    )
    if form.validate_on_submit():
        session = InterviewSession(
            user_id=current_user.id,
            mode=mode,
            category=form.category.data,
            difficulty=form.difficulty.data,
            questions_json=build_questions(form.category.data, form.difficulty.data, 6 if mode == "mock" else 5),
        )
        db.session.add(session)
        db.session.commit()
        return redirect(url_for("growth.interview_session", session_id=session.id))
    return render_template("growth/interview_prep.html", form=form, sessions=sessions, mode=mode)


@bp.route("/interview/<int:session_id>", methods=["GET", "POST"])
@login_required
def interview_session(session_id):
    session = owned_session(session_id)
    if request.method == "POST":
        answers = [request.form.get(f"answer_{index}", "") for index, _ in enumerate(session.questions_json)]
        tech, comm, grammar, report = evaluate_answers(session.questions_json, answers)
        session.answers_json = answers
        session.technical_score = tech
        session.communication_score = comm
        session.grammar_score = grammar
        session.final_report = report
        session.completed_at = datetime.utcnow()
        db.session.commit()
        flash("Interview evaluated.", "success")
        return redirect(url_for("growth.interview_report", session_id=session.id))
    return render_template("growth/interview_session.html", session=session)


@bp.get("/interview/<int:session_id>/report")
@login_required
def interview_report(session_id):
    session = owned_session(session_id)
    return render_template("growth/interview_report.html", session=session)


def owned_resume(document_id):
    document = db.session.get(ResumeDocument, document_id)
    if not document or document.user_id != current_user.id:
        abort(404)
    return document


def owned_session(session_id):
    session = db.session.get(InterviewSession, session_id)
    if not session or session.user_id != current_user.id:
        abort(404)
    return session


def recalculate_stage(stage):
    if stage.tasks:
        done = sum(1 for task in stage.tasks if task.completed)
        stage.progress = round(done / len(stage.tasks) * 100)
    stage.status = "completed" if stage.progress == 100 else "in_progress" if stage.progress else "not_started"
    recalculate_roadmap(stage.roadmap)


def recalculate_roadmap(roadmap_obj):
    if roadmap_obj.stages:
        roadmap_obj.overall_progress = round(sum(stage.progress for stage in roadmap_obj.stages) / len(roadmap_obj.stages))


def seed_learning_resources(plan=None):
    rows = learning_resource_rows_for_plan(plan) if plan else RESOURCE_CATALOG
    existing_urls = {row.url for row in LearningResource.query.with_entities(LearningResource.url).all()}
    for row in rows:
        url = row[8]
        if url in existing_urls:
            continue
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            continue
        db.session.add(
            LearningResource(
                skill_name=row[0],
                title=row[1],
                provider=row[2],
                resource_type=row[3],
                level=row[4],
                cost_type=row[5],
                priority=row[6],
                duration_text=row[7],
                url=url,
                description=row[9],
            )
        )
    db.session.commit()
