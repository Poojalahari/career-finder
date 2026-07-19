import io

import fitz
import pytest

from app import create_app
from app.extensions import db
from app.models import User
from config import TestingConfig


class TestConfig(TestingConfig):
    WTF_CSRF_ENABLED = False


@pytest.fixture()
def app(tmp_path):
    class Config(TestConfig):
        UPLOAD_FOLDER = str(tmp_path / "uploads")
        SUPABASE_AUTH_ENABLED = True
        SUPABASE_URL = "https://test.supabase.co"
        SUPABASE_PUBLISHABLE_KEY = "test-publishable-key"

    app = create_app(Config)
    with app.app_context():
        db.create_all()
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def register(client, email="user@example.com", password="StrongPass1!", name="User Example"):
    return client.post(
        "/register",
        data={"full_name": name, "email": email, "password": password, "confirm_password": password},
        follow_redirects=True,
    )


def login(client, email="user@example.com", password="StrongPass1!"):
    return client.post("/login", data={"email": email, "password": password}, follow_redirects=True)


def create_user(app, user_id="df95655c-9360-4c25-b65d-56f342fc26f1", email="user@example.com", role="student", active=True):
    with app.app_context():
        user = User(id=user_id, email=email, full_name="User Example", role=role, is_active_flag=active, email_verified=True)
        db.session.add(user)
        db.session.commit()
    return user_id


def login_session(client, user_id="df95655c-9360-4c25-b65d-56f342fc26f1"):
    with client.session_transaction() as auth_session:
        auth_session.clear()
        auth_session["_user_id"] = user_id
        auth_session["_fresh"] = True
        auth_session["supabase_access_token"] = "test-access-token"
        auth_session["supabase_refresh_token"] = "test-refresh-token"


@pytest.fixture()
def auth_client(client, app):
    create_user(app)
    login_session(client)
    return client


def make_pdf(text=""):
    doc = fitz.open()
    page = doc.new_page()
    if text:
        page.insert_text((72, 72), text)
    data = doc.tobytes()
    doc.close()
    return io.BytesIO(data)
