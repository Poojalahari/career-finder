import os

import pytest

from app import create_app
from app.services import supabase_auth


def test_live_supabase_login_and_logout():
    email = os.getenv("SUPABASE_SMOKE_EMAIL", "").strip().lower()
    password = os.getenv("SUPABASE_SMOKE_PASSWORD", "")
    if not email or not password:
        pytest.skip("Dedicated Supabase smoke credentials are not configured")

    app = create_app()
    with app.app_context():
        auth_session = supabase_auth.sign_in(email, password)
        assert auth_session.user_id
        assert auth_session.email.lower() == email
        supabase_auth.sign_out(auth_session.access_token)
