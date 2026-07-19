import pytest
from flask import Flask

from app import create_app, validate_production_config
from app.extensions import db
from config import ProductionConfig, TestingConfig


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json["status"] == "ok"
    assert response.json["application"] == "CareerPath ATS"
    assert response.json["database"] == "connected"
    assert response.json["supabase_auth"] == "configured"


def test_health_reports_disabled_supabase(tmp_path):
    class Config(TestingConfig):
        SUPABASE_AUTH_ENABLED = False
        SUPABASE_URL = ""
        SUPABASE_PUBLISHABLE_KEY = ""
        UPLOAD_FOLDER = str(tmp_path / "uploads")

    app = create_app(Config)
    with app.app_context():
        db.create_all()
        response = app.test_client().get("/health")
        assert response.status_code == 200
        assert response.json["database"] == "connected"
        assert response.json["supabase_auth"] == "disabled"
        db.drop_all()


def test_static_assets_load(client):
    assert client.get("/static/css/app.css").status_code == 200
    assert client.get("/static/js/app.js").status_code == 200


def test_404(client):
    assert client.get("/missing").status_code == 404


def test_dashboard_loads(auth_client):
    assert b"Your career command center" in auth_client.get("/dashboard").data


def test_production_debug_disabled():
    assert ProductionConfig.DEBUG is False


def test_missing_production_configuration_names_only():
    app = Flask(__name__)
    app.config.update(ENV="production", DEBUG=False, TESTING=False, SECRET_KEY="dev-only-change-me")
    with pytest.raises(RuntimeError, match="DATABASE_URL") as error:
        validate_production_config(app)
    assert "replace-me" not in str(error.value)


def test_production_configuration_requires_postgresql():
    app = Flask(__name__)
    app.config.update(
        ENV="production",
        DEBUG=False,
        TESTING=False,
        SECRET_KEY="a" * 32,
        DATABASE_URL="sqlite:///production.db",
        SQLALCHEMY_DATABASE_URI="sqlite:///production.db",
        SUPABASE_AUTH_ENABLED=True,
        SUPABASE_URL="https://example.supabase.co",
        SUPABASE_PUBLISHABLE_KEY="publishable-value",
        SUPABASE_SECRET_KEY="secret-value",
        SUPABASE_EMAIL_REDIRECT_URL="https://example.onrender.com/auth/callback",
        SUPABASE_STORAGE_BUCKET="career-documents",
        ADMIN_EMAILS="admin@example.com",
    )
    with pytest.raises(RuntimeError, match="PostgreSQL required"):
        validate_production_config(app)

    app.config.update(
        DATABASE_URL="postgresql://configured",
        SQLALCHEMY_DATABASE_URI="postgresql+psycopg://configured",
    )
    validate_production_config(app)
