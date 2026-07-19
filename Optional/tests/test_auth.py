import io
from urllib.error import HTTPError

from app.extensions import db
from app.auth.services import register_user
from app.models import CareerAssessment, User
from app.services.supabase_auth import SupabaseAuthError, SupabaseSession
from tests.conftest import create_user, login, login_session, register


AUTH_ID = "df95655c-9360-4c25-b65d-56f342fc26f1"


def auth_response(email="user@example.com"):
    return SupabaseSession(AUTH_ID, email, "User Example", True, "access-token", "refresh-token")


def test_register_page_loads(client):
    assert client.get("/register").status_code == 200


def test_registration_disabled_returns_safe_structured_error(client, app, monkeypatch):
    monkeypatch.setattr("app.auth.services.supabase_auth.enabled", lambda: False)

    response = register(client)

    assert response.status_code == 200
    assert b"Registration is temporarily unavailable" in response.data
    assert b"SUPABASE" not in response.data
    with app.app_context():
        user, error = register_user("User Example", "user@example.com", "StrongPass1!")
    assert user is None
    assert error == {
        "code": "auth_not_configured",
        "message": "Registration is temporarily unavailable. Please try again later.",
    }


def test_registration_route_handles_malformed_service_error(client, monkeypatch):
    monkeypatch.setattr("app.auth.routes.register_user", lambda *args: (None, "internal configuration detail"))

    response = register(client)

    assert response.status_code == 200
    assert b"Registration is temporarily unavailable" in response.data
    assert b"internal configuration detail" not in response.data


def test_invalid_signup_response_is_safe(client, monkeypatch):
    monkeypatch.setattr("app.auth.services.supabase_auth.sign_up", lambda *args: ["invalid"])

    response = register(client)

    assert response.status_code == 200
    assert b"could not create your account" in response.data
    assert b"invalid" not in response.data


def test_invalid_immediate_session_response_is_safe(client, monkeypatch):
    monkeypatch.setattr(
        "app.auth.services.supabase_auth.sign_up",
        lambda *args: {
            "user": {"id": AUTH_ID, "email": "user@example.com", "user_metadata": "invalid"},
            "access_token": "not-returned-to-browser",
        },
    )

    response = register(client)

    assert response.status_code == 200
    assert b"Registration is temporarily unavailable" in response.data
    assert b"not-returned-to-browser" not in response.data


def test_student_registration_sends_safe_metadata(client, app, monkeypatch):
    captured = {}

    def sign_up(email, password, full_name):
        captured.update(email=email, password=password, full_name=full_name)
        return {"id": AUTH_ID, "email": email, "identities": [{}]}

    monkeypatch.setattr("app.auth.services.supabase_auth.sign_up", sign_up)
    response = register(client, email="USER@Example.COM")
    assert b"verification link was sent to your email" in response.data
    assert captured["email"] == "user@example.com"
    assert set(captured) == {"email", "password", "full_name"}
    with app.app_context():
        assert User.query.count() == 0


def test_duplicate_and_weak_registration_rejected(client, monkeypatch):
    monkeypatch.setattr(
        "app.auth.services.supabase_auth.sign_up",
        lambda *args: (_ for _ in ()).throw(SupabaseAuthError("already registered", code="user_already_exists", status=422)),
    )
    response = register(client)
    assert b"An account already exists with this email" in response.data
    assert response.request.path == "/login"
    assert response.request.args.to_dict() == {"email": "user@example.com", "reason": "account-exists"}
    assert b'value="user@example.com"' in response.data
    assert b'value="StrongPass1!"' not in response.data
    response = client.post("/register", data={"full_name": "Bad", "email": "bad@example.com", "password": "weak", "confirm_password": "weak"})
    assert b"10+ characters" in response.data


def test_signup_errors_are_not_mapped_to_duplicate(client, monkeypatch):
    cases = (
        (SupabaseAuthError("weak", code="weak_password"), b"stronger password"),
        (SupabaseAuthError("rate", code="over_request_rate_limit", status=429), b"Too many attempts"),
        (SupabaseAuthError("offline", code="network_error", kind="network"), b"Unable to connect"),
        (SupabaseAuthError("broken", code="unexpected_failure", status=500), b"could not create your account"),
    )
    for error, expected in cases:
        monkeypatch.setattr("app.auth.services.supabase_auth.sign_up", lambda *args, error=error: (_ for _ in ()).throw(error))
        response = register(client)
        assert expected in response.data
        assert b"already exists" not in response.data


def test_missing_signup_session_is_confirmation_not_duplicate(client, monkeypatch):
    monkeypatch.setattr(
        "app.auth.services.supabase_auth.sign_up",
        lambda *args: {"id": AUTH_ID, "identities": [], "email": "user@example.com"},
    )
    response = register(client)
    assert b"verification link was sent to your email" in response.data
    assert b"already exists" not in response.data


def test_email_token_confirmation_logs_in_and_opens_dashboard(client, monkeypatch):
    monkeypatch.setattr("app.auth.services.supabase_auth.verify_email", lambda token: auth_response())
    response = client.get("/auth/callback?token_hash=safe-hash&type=email", follow_redirects=True)
    assert response.request.path == "/dashboard"
    assert b"Email verified successfully" in response.data


def test_implicit_email_confirmation_logs_in_without_tokens_in_url(client, monkeypatch):
    monkeypatch.setattr(
        "app.auth.services.supabase_auth.get_user",
        lambda token: {
            "id": AUTH_ID,
            "email": "user@example.com",
            "email_confirmed_at": "now",
            "user_metadata": {"full_name": "User Example"},
        },
    )
    response = client.post(
        "/auth/session-callback",
        json={"access_token": "access-token", "refresh_token": "refresh-token"},
    )
    assert response.status_code == 200
    assert response.json == {"redirect": "/dashboard"}
    with client.session_transaction() as auth_session:
        assert auth_session["supabase_access_token"] == "access-token"
        assert auth_session["supabase_refresh_token"] == "refresh-token"


def test_password_confirmation_must_match(client):
    response = client.post(
        "/register",
        data={"full_name": "User", "email": "user@example.com", "password": "StrongPass1!", "confirm_password": "Different1!"},
    )
    assert b"Passwords must match" in response.data


def test_registration_with_immediate_session_logs_user_in(client, app, monkeypatch):
    monkeypatch.setattr(
        "app.auth.services.supabase_auth.sign_up",
        lambda *args: {
            "user": {"id": AUTH_ID, "email": "user@example.com", "email_confirmed_at": "now", "user_metadata": {"full_name": "User Example"}, "identities": [{}]},
            "session": {"access_token": "access-token"},
            "access_token": "access-token",
            "refresh_token": "refresh-token",
        },
    )
    response = register(client)
    assert b"Dashboard" in response.data
    with app.app_context():
        assert db.session.get(User, AUTH_ID) is not None


def test_login_creates_uuid_profile_and_logout_clears_session(client, app, monkeypatch):
    monkeypatch.setattr("app.auth.services.supabase_auth.sign_in", lambda *args: auth_response())
    monkeypatch.setattr("app.auth.routes.supabase_auth.sign_out", lambda token: None)
    assert b"Dashboard" in login(client).data
    assert "access-token" not in client.get_cookie("session").value
    with app.app_context():
        profile = db.session.get(User, AUTH_ID)
        assert profile.role == "student"
        assert profile.id == AUTH_ID
    response = client.post("/logout", follow_redirects=True)
    assert b"Sign in" in response.data
    with client.session_transaction() as auth_session:
        assert "supabase_access_token" not in auth_session
        assert "supabase_refresh_token" not in auth_session
        assert "_user_id" not in auth_session


def test_wrong_password_is_generic(client, monkeypatch):
    monkeypatch.setattr("app.auth.services.supabase_auth.sign_in", lambda *args: (_ for _ in ()).throw(SupabaseAuthError("specific provider message")))
    response = login(client, password="WrongPass1!")
    assert b"Invalid email or password" in response.data
    assert b"specific provider message" not in response.data


def test_unconfirmed_email_has_safe_actionable_message(client, monkeypatch):
    monkeypatch.setattr(
        "app.auth.services.supabase_auth.sign_in",
        lambda *args: (_ for _ in ()).throw(SupabaseAuthError("provider detail", code="email_not_confirmed")),
    )
    assert b"Confirm your email" in login(client).data


def test_network_failure_has_temporary_message(client, monkeypatch):
    monkeypatch.setattr(
        "app.auth.services.supabase_auth.sign_in",
        lambda *args: (_ for _ in ()).throw(SupabaseAuthError("network detail", code="network_error", kind="network")),
    )
    response = login(client)
    assert b"temporarily unavailable" in response.data
    assert b"network detail" not in response.data


def test_provider_errors_are_sanitized_in_logs_and_response(client, caplog, monkeypatch):
    secret = "sb_secret_must_never_appear"

    def reject(*args, **kwargs):
        body = ('{"error_code":"invalid_credentials","msg":"Wrong login for private@example.com ' + secret + '"}').encode()
        raise HTTPError("https://supabase.invalid", 400, "Bad Request", {}, io.BytesIO(body))

    monkeypatch.setattr("app.services.supabase_auth.urlopen", reject)
    response = login(client)
    combined = caplog.text + response.get_data(as_text=True)
    assert "private@example.com" not in combined
    assert secret not in combined
    assert "[email]" in caplog.text
    assert "[credential]" in caplog.text


def test_inactive_user_is_blocked(client, app, monkeypatch):
    create_user(app, active=False)
    monkeypatch.setattr("app.auth.services.supabase_auth.sign_in", lambda *args: auth_response())
    response = login(client)
    assert b"inactive" in response.data
    assert b"Dashboard" not in response.data


def test_first_supabase_login_transfers_legacy_owned_records(client, app, monkeypatch):
    legacy_id = "a364fb83-7028-4e73-8615-857b31cc12b2"
    create_user(app, user_id=legacy_id)
    with app.app_context():
        db.session.add(CareerAssessment(
            user_id=legacy_id,
            skills="Python",
            interests="AI",
            cgpa=8.0,
            certifications="",
            recommended_career="Data Scientist",
            confidence_score=80,
            explanation="Match",
            result_json={},
        ))
        db.session.commit()
    monkeypatch.setattr("app.auth.services.supabase_auth.sign_in", lambda *args: auth_response())
    assert b"Dashboard" in login(client).data
    with app.app_context():
        assert db.session.get(User, legacy_id) is None
        assert CareerAssessment.query.one().user_id == AUTH_ID


def test_session_restoration_and_expired_token_refresh(client, app, monkeypatch):
    create_user(app)
    app.config.update(SUPABASE_AUTH_ENABLED=True, AUTH_SESSION_VALIDATION=True)
    calls = {"get": 0, "refresh": 0}

    def get_user(token):
        calls["get"] += 1
        if token == "expired":
            raise SupabaseAuthError("expired")
        return {"id": AUTH_ID, "email": "user@example.com"}

    monkeypatch.setattr("app.auth.services.supabase_auth.get_user", get_user)
    monkeypatch.setattr("app.auth.services.supabase_auth.refresh", lambda token: (calls.__setitem__("refresh", calls["refresh"] + 1) or auth_response()))
    with client.session_transaction() as auth_session:
        auth_session["supabase_access_token"] = "expired"
        auth_session["supabase_refresh_token"] = "refresh-token"
    assert client.get("/dashboard").status_code == 200
    assert calls["refresh"] == 1
    with client.session_transaction() as auth_session:
        assert auth_session["supabase_access_token"] == "access-token"


def test_password_reset_request_never_reveals_account(client, monkeypatch):
    monkeypatch.setattr("app.auth.routes.supabase_auth.request_password_reset", lambda email: (_ for _ in ()).throw(SupabaseAuthError("not found")))
    response = client.post("/forgot-password", data={"email": "missing@example.com"}, follow_redirects=True)
    assert b"If that account exists" in response.data
    assert b"not found" not in response.data


def test_password_recovery_callback_updates_password(client, monkeypatch):
    monkeypatch.setattr("app.auth.services.supabase_auth.verify_recovery", lambda token: auth_response())
    updated = {}
    monkeypatch.setattr(
        "app.auth.routes.supabase_auth.update_password",
        lambda token, password: updated.update(token=token, password=password),
    )

    response = client.get("/auth/callback?type=recovery&token_hash=valid", follow_redirects=True)
    assert b"Reset password" in response.data
    response = client.post(
        "/reset-password",
        data={"password": "NewStrong1!", "confirm_password": "NewStrong1!"},
        follow_redirects=True,
    )
    assert b"Password updated successfully" in response.data
    assert updated == {"token": "access-token", "password": "NewStrong1!"}


def test_role_authorization(client, app):
    create_user(app, role="student")
    login_session(client)
    assert client.get("/admin/").status_code == 403

    with app.app_context():
        profile = db.session.get(User, AUTH_ID)
        profile.role = "counsellor"
        db.session.commit()
        db.session.expire_all()
    assert client.get("/admin/").status_code == 403
    assert client.get("/admin/system").status_code == 403

    with app.app_context():
        profile = db.session.get(User, AUTH_ID)
        profile.role = "admin"
        db.session.commit()
        db.session.expire_all()
    assert client.get("/admin/").status_code == 200
    assert client.get("/admin/system").status_code == 403

    with app.app_context():
        profile = db.session.get(User, AUTH_ID)
        profile.role = "super_admin"
        db.session.commit()
        db.session.expire_all()
    assert client.get("/admin/system").status_code == 200


def test_anonymous_user_is_redirected_from_protected_route(client):
    response = client.get("/dashboard")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_authenticated_user_is_redirected_from_auth_pages(client, app):
    create_user(app)
    login_session(client)
    for path in ("/login", "/register"):
        response = client.get(path)
        assert response.status_code == 302
        assert response.headers["Location"].endswith("/dashboard")
