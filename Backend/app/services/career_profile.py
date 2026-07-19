from app.extensions import db
from app.models import CareerAssessment, CareerProfile, CareerRoadmap
from app.growth.services import canonical_career, completed_skill_names


def get_or_create_profile(user):
    profile = CareerProfile.query.filter_by(user_id=user.id).first()
    if profile:
        return profile
    latest_roadmap = CareerRoadmap.query.filter_by(user_id=user.id, is_active=True).order_by(CareerRoadmap.updated_at.desc()).first()
    latest_assessment = CareerAssessment.query.filter_by(user_id=user.id).order_by(CareerAssessment.created_at.desc()).first()
    track = latest_roadmap.learning_track if latest_roadmap else latest_assessment.recommended_career if latest_assessment else "Python"
    profile = CareerProfile(
        user_id=user.id,
        learning_track=canonical_career(track),
        current_level=latest_roadmap.current_level if latest_roadmap else "beginner",
        known_skills=latest_roadmap.known_skills if latest_roadmap else "",
        weekly_hours=latest_roadmap.weekly_hours if latest_roadmap else 8,
        target_date=latest_roadmap.target_date if latest_roadmap else None,
        source="roadmap" if latest_roadmap else "assessment" if latest_assessment else "default",
        completed_skills_json=list(completed_skill_names(CareerRoadmap.query.filter_by(user_id=user.id).all())),
    )
    db.session.add(profile)
    db.session.flush()
    return profile


def update_profile(user, learning_track=None, known_skills=None, current_level=None, weekly_hours=None, target_date=None, source="manual"):
    profile = get_or_create_profile(user)
    if learning_track:
        profile.learning_track = canonical_career(learning_track)
    if known_skills is not None:
        profile.known_skills = known_skills
    if current_level:
        profile.current_level = current_level
    if weekly_hours:
        profile.weekly_hours = max(1, min(int(weekly_hours), 80))
    if target_date is not None:
        profile.target_date = target_date
    profile.source = source
    profile.missing_skills_json = []
    profile.completed_skills_json = list(completed_skill_names(CareerRoadmap.query.filter_by(user_id=user.id).all()))
    db.session.flush()
    return profile
