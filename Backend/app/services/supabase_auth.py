import json
import re
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from flask import current_app, g, has_request_context, request

from config import configured


class SupabaseAuthError(RuntimeError):
    def __init__(self, message: str, *, code: str = "unknown", kind: str = "provider", status: int | None = None):
        super().__init__(message)
        self.code = code
        self.kind = kind
        self.status = status


@dataclass(frozen=True)
class SupabaseAuthClient:
    api_key: str

    def request(self, path: str, payload: dict | None = None, *, operation: str, token: str | None = None, method: str = "POST") -> dict:
        return _request(path, payload, operation=operation, api_key=self.api_key, token=token, method=method)


@dataclass(frozen=True)
class SupabaseSession:
    user_id: str
    email: str
    full_name: str
    email_verified: bool
    access_token: str
    refresh_token: str


def enabled() -> bool:
    url = str(current_app.config.get("SUPABASE_URL", ""))
    key = str(current_app.config.get("SUPABASE_PUBLISHABLE_KEY", ""))
    return bool(current_app.config.get("SUPABASE_AUTH_ENABLED") and configured(url) and configured(key))


def _safe_message(message: str) -> str:
    message = re.sub(r"[\w.+-]+@[\w.-]+", "[email]", message)
    message = re.sub(r"(?:sb_(?:secret|publishable)_[\w-]+|eyJ[\w.-]+)", "[credential]", message)
    return message.replace("\r", " ").replace("\n", " ")[:200]


def _log_failure(operation: str, error: SupabaseAuthError) -> None:
    current_app.logger.warning(
        "supabase_auth_failure operation=%s error_type=%s error_name=%s code=%s status=%s path=%s request_id=%s message=%s",
        operation,
        error.kind,
        type(error).__name__,
        error.code,
        error.status,
        request.path if has_request_context() else "startup",
        getattr(g, "request_id", "-") if has_request_context() else "-",
        _safe_message(str(error)),
    )


def _public_client() -> SupabaseAuthClient:
    return SupabaseAuthClient(str(current_app.config.get("SUPABASE_PUBLISHABLE_KEY", "")))


def _privileged_client() -> SupabaseAuthClient:
    return SupabaseAuthClient(str(current_app.config.get("SUPABASE_SECRET_KEY", "")))


def _request(path: str, payload: dict | None = None, *, operation: str, api_key: str, token: str | None = None, method: str = "POST") -> dict:
    base_url = current_app.config.get("SUPABASE_URL", "")
    if not configured(base_url) or not configured(api_key):
        error = SupabaseAuthError("Authentication service is not configured.", code="invalid_configuration", kind="configuration")
        _log_failure(operation, error)
        raise error

    headers = {"apikey": api_key, "Content-Type": "application/json", "Authorization": f"Bearer {token or api_key}"}
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(f"{base_url}/auth/v1/{path.lstrip('/')}", data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=12) as response:
            try:
                result = json.loads(response.read().decode("utf-8") or "{}")
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                error = SupabaseAuthError(
                    "Authentication service returned an invalid response.",
                    code="invalid_response",
                    kind="provider",
                )
                _log_failure(operation, error)
                raise error from exc
            if not isinstance(result, dict):
                error = SupabaseAuthError(
                    "Authentication service returned an invalid response.",
                    code="invalid_response",
                    kind="provider",
                )
                _log_failure(operation, error)
                raise error
            return result
    except HTTPError as exc:
        try:
            body_json = json.loads(exc.read().decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            body_json = {}
        message = body_json.get("msg") or body_json.get("message") or "Authentication request failed."
        error = SupabaseAuthError(message, code=str(body_json.get("error_code") or exc.code), kind="provider", status=exc.code)
        _log_failure(operation, error)
        raise error from exc
    except (URLError, TimeoutError) as exc:
        error = SupabaseAuthError("Authentication service is temporarily unavailable.", code="network_error", kind="network")
        _log_failure(operation, error)
        raise error from exc


def _session(response: dict) -> SupabaseSession:
    user = response.get("user") or {}
    metadata = user.get("user_metadata") or {}
    return SupabaseSession(
        user_id=str(user.get("id", "")),
        email=str(user.get("email", "")),
        full_name=str(metadata.get("full_name", "")).strip(),
        email_verified=bool(user.get("email_confirmed_at") or user.get("confirmed_at")),
        access_token=str(response.get("access_token", "")),
        refresh_token=str(response.get("refresh_token", "")),
    )


def session_from_response(response: dict) -> SupabaseSession:
    return _session(response)


def sign_up(email: str, password: str, full_name: str) -> dict:
    redirect_url = current_app.config.get("SUPABASE_EMAIL_REDIRECT_URL", "")
    path = f"signup?redirect_to={quote(redirect_url, safe='')}" if redirect_url else "signup"
    return _public_client().request(path, {"email": email, "password": password, "data": {"full_name": full_name}}, operation="signup")


def sign_in(email: str, password: str) -> SupabaseSession:
    response = _public_client().request("token?grant_type=password", {"email": email, "password": password}, operation="login")
    session = _session(response)
    if not session.user_id or not session.access_token:
        error = SupabaseAuthError("Authentication response did not contain a user session.", code="missing_session")
        _log_failure("login", error)
        raise error
    return session


def refresh(refresh_token: str) -> SupabaseSession:
    return _session(_public_client().request("token?grant_type=refresh_token", {"refresh_token": refresh_token}, operation="refresh"))


def get_user(access_token: str) -> dict:
    return _public_client().request("user", None, operation="get_user", token=access_token, method="GET")


def sign_out(access_token: str) -> None:
    _public_client().request("logout", {}, operation="logout", token=access_token)


def request_password_reset(email: str) -> None:
    redirect_url = current_app.config.get("SUPABASE_EMAIL_REDIRECT_URL", "")
    path = f"recover?redirect_to={quote(redirect_url, safe='')}" if redirect_url else "recover"
    _public_client().request(path, {"email": email}, operation="password_reset")


def verify_recovery(token_hash: str) -> SupabaseSession:
    return _session(_public_client().request("verify", {"token_hash": token_hash, "type": "recovery"}, operation="verify_recovery"))


def verify_email(token_hash: str) -> SupabaseSession:
    return _session(_public_client().request("verify", {"token_hash": token_hash, "type": "email"}, operation="verify_email"))


def update_password(access_token: str, new_password: str) -> None:
    _public_client().request("user", {"password": new_password}, operation="update_password", token=access_token, method="PUT")


def update_email(access_token: str, email: str) -> None:
    _public_client().request("user", {"email": email}, operation="update_email", token=access_token, method="PUT")


def delete_user(user_id: str) -> None:
    if not configured(current_app.config.get("SUPABASE_SECRET_KEY")):
        raise SupabaseAuthError("Account deletion is not configured.")
    _privileged_client().request(f"admin/users/{user_id}", {}, operation="delete_user", method="DELETE")
