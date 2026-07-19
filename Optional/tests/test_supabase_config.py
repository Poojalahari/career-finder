from app import create_app
from app.services import supabase_auth
from config import TestingConfig


def test_placeholder_configuration_is_rejected():
    class Config(TestingConfig):
        SUPABASE_AUTH_ENABLED = True
        SUPABASE_URL = "https://project_id.supabase.co"
        SUPABASE_PUBLISHABLE_KEY = "replace-me"

    app = create_app(Config)
    with app.app_context():
        assert not supabase_auth.enabled()


def test_missing_configuration_is_rejected():
    class Config(TestingConfig):
        SUPABASE_AUTH_ENABLED = True
        SUPABASE_URL = ""
        SUPABASE_PUBLISHABLE_KEY = ""

    app = create_app(Config)
    with app.app_context():
        assert not supabase_auth.enabled()


def test_startup_logs_key_presence_without_values(caplog):
    class Config(TestingConfig):
        SUPABASE_AUTH_ENABLED = True
        SUPABASE_URL = "https://example.supabase.co"
        SUPABASE_PUBLISHABLE_KEY = "publishable-sensitive-value"
        SUPABASE_SECRET_KEY = "secret-sensitive-value"

    create_app(Config)
    message = caplog.text
    assert "Supabase URL configured: yes" in message
    assert "Supabase public key configured: yes" in message
    assert "Supabase privileged key configured: yes" in message
    assert "publishable-sensitive-value" not in message
    assert "secret-sensitive-value" not in message


def test_cookie_and_csrf_configuration():
    assert TestingConfig.SESSION_COOKIE_HTTPONLY is True
    assert TestingConfig.SESSION_COOKIE_SAMESITE == "Lax"
    assert TestingConfig.SESSION_COOKIE_SECURE is False
    assert TestingConfig.WTF_CSRF_ENABLED is True

    from config import ProductionConfig

    assert ProductionConfig.SESSION_COOKIE_SECURE is True
