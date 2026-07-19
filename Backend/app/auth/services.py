from datetime import datetime, timezone
from typing import TypedDict
from uuid import UUID

from flask import current_app, g, session
from flask_login import current_user, login_user, logout_user
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models import User
from app.services import supabase_auth
from app.services.security import normalize_email


INVALID_CREDENTIALS = "Invalid email or password."
DUPLICATE_SIGNUP_CODES = {"email_exists", "user_already_exists"}


class RegistrationError(TypedDict):
    code: str
    message: str


def registration_error(code: str, message: str) -> RegistrationError:
    return {"code": code, "message": message}


def _request_id() -> str:
    return str(getattr(g, "request_id", "-"))


def map_signup_error(error: supabase_auth.SupabaseAuthError) -> RegistrationError:
    code = error.code
    if code in DUPLICATE_SIGNUP_CODES:
        return registration_error("account_exists", "An account already exists with this email. Please log in.")
    if code == "weak_password":
        return registration_error(code, "Please choose a stronger password.")
    if code in {"email_address_invalid", "validation_failed"}:
        return registration_error(code, "Please enter a valid email address.")
    if code in {"signup_disabled", "email_provider_disabled"}:
        return registration_error(code, "New account registration is currently unavailable.")
    if code in {"over_request_rate_limit", "over_email_send_rate_limit", "429"}:
        return registration_error(code, "Too many attempts. Please wait and try again.")
    if error.kind == "network" or code in {"network_error", "request_timeout"}:
        return registration_error(code, "Unable to connect. Check your connection and try again.")
    return registration_error(code, "We could not create your account right now. Please try again.")


def register_user(full_name: str, email: str, password: str) -> tuple[dict | None, RegistrationError | None]:
    if not supabase_auth.enabled():
        current_app.logger.error(
            "registration_failure operation=configuration_check request_id=%s error_type=ConfigurationError",
            _request_id(),
        )
        return None, registration_error(
            "auth_not_configured",
            "Registration is temporarily unavailable. Please try again later.",
        )
    current_app.logger.info("registration_progress operation=supabase_signup request_id=%s", _request_id())
    try:
        response = supabase_auth.sign_up(normalize_email(email), password, full_name.strip())
    except supabase_auth.SupabaseAuthError as exc:
        return None, map_signup_error(exc)
    if not isinstance(response, dict):
        current_app.logger.error(
            "registration_failure operation=response_parsing request_id=%s error_type=%s",
            _request_id(),
            type(response).__name__,
        )
        return None, registration_error("unexpected_response", "We could not create your account right now. Please try again.")
    # GoTrue returns the pending user directly when email confirmation is required,
    # but nests it under "user" when a session is issued.
    user = response.get("user") or (response if response.get("id") else {})
    if not isinstance(user, dict):
        user = {}
    try:
        UUID(str(user.get("id", "")))
    except (TypeError, ValueError):
        current_app.logger.error(
            "registration_failure operation=response_parsing request_id=%s error_type=InvalidUserId",
            _request_id(),
        )
        return None, registration_error("unexpected_response", "We could not create your account right now. Please try again.")
    if response.get("session") or response.get("access_token"):
        current_app.logger.info("registration_progress operation=session_initialization request_id=%s", _request_id())
        try:
            auth_session = supabase_auth.session_from_response(response)
            if auth_session.user_id != user["id"]:
                return None, registration_error("session_mismatch", "We could not create your account right now. Please try again.")
            authenticated, error = _establish_login(auth_session)
        except Exception as exc:
            db.session.rollback()
            current_app.logger.error(
                "registration_failure operation=session_initialization request_id=%s error_type=%s",
                _request_id(),
                type(exc).__name__,
            )
            return None, registration_error("registration_unavailable", "Registration is temporarily unavailable. Please try again later.")
        if not authenticated:
            return None, registration_error("profile_error", "Your account was created, but your profile could not be prepared. Please try signing in.")
        current_app.logger.info("registration_complete operation=authenticated_signup request_id=%s", _request_id())
        return {"user": user, "authenticated": True}, None
    current_app.logger.info("registration_complete operation=confirmation_required request_id=%s", _request_id())
    return {"user": user, "authenticated": False}, None


def _load_profile(user_id: str, email: str, full_name: str = "") -> User:
    profile = db.session.get(User, user_id)
    if profile:
        return profile
    normalized_email = normalize_email(email)
    legacy = User.query.filter_by(email=normalized_email).first()
    if legacy and legacy.id != user_id:
        from app.models import CareerAssessment, CareerProfile, CareerRoadmap, ChatConversation, InterviewSession, LearningProgress, ResumeDocument, ResumeScan, UserLearningResource

        legacy_id = legacy.id
        legacy.email = f"legacy-{legacy_id}@invalid.local"
        profile = User(id=user_id, email=normalized_email, full_name=full_name or legacy.full_name, role=legacy.role, email_verified=True)
        db.session.add(profile)
        db.session.flush()
        for model in (
            CareerAssessment,
            ResumeScan,
            LearningProgress,
            CareerProfile,
            CareerRoadmap,
            UserLearningResource,
            ResumeDocument,
            InterviewSession,
            ChatConversation,
        ):
            model.query.filter_by(user_id=legacy_id).update({"user_id": user_id}, synchronize_session=False)
        db.session.delete(legacy)
        db.session.flush()
        return profile
    profile = User(id=user_id, email=normalized_email, full_name=full_name or email.split("@", 1)[0], role="student", email_verified=True)
    db.session.add(profile)
    db.session.flush()
    return profile


def _bootstrap_first_super_admin(profile: User) -> None:
    allowed = {value.strip().lower() for value in current_app.config.get("ADMIN_EMAILS", "").split(",") if value.strip()}
    if profile.role == "student" and profile.email in allowed and not User.query.filter_by(role="super_admin").first():
        profile.role = "super_admin"


def _establish_login(auth_session: supabase_auth.SupabaseSession, remember: bool = False) -> tuple[bool, str | None]:
    if not auth_session.user_id or not auth_session.email_verified:
        return False, "Verify your email before signing in."
    try:
        current_app.logger.info("registration_progress operation=profile_sync request_id=%s", _request_id())
        profile = _load_profile(auth_session.user_id, auth_session.email, auth_session.full_name)
        _bootstrap_first_super_admin(profile)
        if not profile.is_active:
            db.session.rollback()
            return False, "This account is inactive. Contact support."
        profile.email = normalize_email(auth_session.email)
        profile.email_verified = True
        profile.last_login_at = datetime.now(timezone.utc)
        db.session.commit()
    except SQLAlchemyError as exc:
        db.session.rollback()
        current_app.logger.error(
            "registration_failure operation=database_commit request_id=%s error_type=%s",
            _request_id(),
            type(exc).__name__,
        )
        return False, "Unable to load your account. Try again later."

    session.clear()
    if hasattr(current_app.session_interface, "regenerate"):
        current_app.session_interface.regenerate(session)
    session["supabase_access_token"] = auth_session.access_token
    session["supabase_refresh_token"] = auth_session.refresh_token
    login_user(profile, remember=remember, fresh=True)
    current_app.logger.info("registration_progress operation=session_initialized request_id=%s", _request_id())
    return True, None


def authenticate(email: str, password: str, remember: bool = False) -> tuple[bool, str | None]:
    if not supabase_auth.enabled():
        return False, "Supabase authentication is not configured."
    try:
        auth_session = supabase_auth.sign_in(normalize_email(email), password)
    except supabase_auth.SupabaseAuthError as exc:
        if exc.code in {"email_not_confirmed", "unconfirmed_email"}:
            return False, "Confirm your email before signing in."
        if exc.kind in {"network", "configuration"} or exc.code in {"over_request_rate_limit", "over_email_send_rate_limit", "429"}:
            return False, "Sign-in is temporarily unavailable. Try again shortly."
        return False, INVALID_CREDENTIALS
    return _establish_login(auth_session, remember)


def restore_authenticated_session() -> None:
    if not current_app.config.get("AUTH_SESSION_VALIDATION", True) or not supabase_auth.enabled():
        return
    access_token = session.get("supabase_access_token")
    refresh_token = session.get("supabase_refresh_token")
    if not access_token:
        if current_user.is_authenticated:
            logout_user()
            session.clear()
        return
    try:
        user_data = supabase_auth.get_user(access_token)
    except supabase_auth.SupabaseAuthError:
        if not refresh_token:
            logout_user()
            session.clear()
            return
        try:
            refreshed = supabase_auth.refresh(refresh_token)
            session["supabase_access_token"] = refreshed.access_token
            session["supabase_refresh_token"] = refreshed.refresh_token
            user_data = supabase_auth.get_user(refreshed.access_token)
        except supabase_auth.SupabaseAuthError:
            logout_user()
            session.clear()
            return
    user_id = str(user_data.get("id", ""))
    profile = db.session.get(User, user_id) if user_id else None
    if not profile or not profile.is_active:
        logout_user()
        session.clear()
    elif not current_user.is_authenticated:
        login_user(profile, fresh=False)


def complete_recovery(token_hash: str) -> tuple[bool, str | None]:
    try:
        return _establish_login(supabase_auth.verify_recovery(token_hash))
    except supabase_auth.SupabaseAuthError:
        return False, "The reset link is invalid or expired."


def complete_email_confirmation(token_hash: str) -> tuple[bool, str | None]:
    try:
        return _establish_login(supabase_auth.verify_email(token_hash))
    except supabase_auth.SupabaseAuthError:
        return False, "The confirmation link is invalid or expired."


def complete_implicit_confirmation(access_token: str, refresh_token: str) -> tuple[bool, str | None]:
    try:
        user = supabase_auth.get_user(access_token)
    except supabase_auth.SupabaseAuthError:
        return False, "The confirmation link is invalid or expired."
    return _establish_login(supabase_auth.session_from_response({
        "user": user,
        "access_token": access_token,
        "refresh_token": refresh_token,
    }))
