import pytest
from flask import Flask

from app import validate_production_config
from config import ProductionConfig


def test_health(client):
    response = client.get("/health")
    assert response.json["status"] == "ok"
    assert response.json["application"] == "CareerPath ATS"


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
