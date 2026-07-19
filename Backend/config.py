import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv
from cachelib.file import FileSystemCache
from redis import Redis


BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
load_dotenv(PROJECT_ROOT / ".env", override=False)
DEFAULT_DATABASE_URI = f"sqlite:///{(BASE_DIR / 'instance' / 'career.db').as_posix()}"
PLACEHOLDERS = ("project_id", "replace-me", "replace-with", "your-domain.example.com", "change-me")


def configured(value: str | None) -> bool:
    text = str(value or "").strip().lower()
    return bool(text) and not any(marker in text for marker in PLACEHOLDERS)


def bounded_int(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer.") from exc
    if not minimum <= value <= maximum:
        raise RuntimeError(f"{name} must be between {minimum} and {maximum}.")
    return value


def database_uri() -> str:
    value = os.getenv("DATABASE_URL")
    if not value:
        return DEFAULT_DATABASE_URI
    if os.getenv("FLASK_ENV", "development").lower() != "production" and any(
        marker in value.lower() for marker in ("project_id", "database_password", "replace")
    ):
        return DEFAULT_DATABASE_URI
    if value.startswith("sqlite:///") and not value.startswith("sqlite:////"):
        raw_path = value.removeprefix("sqlite:///")
        if len(raw_path) > 1 and raw_path[1] == ":":
            return f"sqlite:///{Path(raw_path).as_posix()}"
        return f"sqlite:///{(BASE_DIR / raw_path).resolve().as_posix()}"
    if value.startswith("postgres://"):
        value = "postgresql://" + value.removeprefix("postgres://")
    if value.startswith("postgresql://"):
        return "postgresql+psycopg://" + value.removeprefix("postgresql://")
    return value


class Config:
    ENV = os.getenv("FLASK_ENV", "development").lower()
    DATABASE_URL = os.getenv("DATABASE_URL", "")
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY") or os.getenv("SECRET_KEY", "dev-only-change-me")
    SQLALCHEMY_DATABASE_URI = database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True, "pool_recycle": 300}
    WTF_CSRF_TIME_LIMIT = 3600
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    MAX_CONTENT_LENGTH = bounded_int("MAX_CONTENT_LENGTH", 10 * 1024 * 1024, 1024, 50 * 1024 * 1024)
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", str(BASE_DIR / "uploads"))
    MAX_PDF_PAGES = bounded_int("MAX_PDF_PAGES", 10, 1, 100)
    RESUME_RETENTION_DAYS = int(os.getenv("RESUME_RETENTION_DAYS", "90"))
    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")
    OCR_ENABLED = os.getenv("OCR_ENABLED", "false").lower() == "true"
    STORE_EXTRACTED_TEXT = os.getenv("STORE_EXTRACTED_TEXT", "false").lower() == "true"
    ADMIN_EMAILS = os.getenv("ADMIN_EMAILS", "")
    SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
    SUPABASE_PUBLISHABLE_KEY = os.getenv("SUPABASE_PUBLISHABLE_KEY") or os.getenv("SUPABASE_ANON_KEY", "")
    SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    SUPABASE_ANON_KEY = SUPABASE_PUBLISHABLE_KEY
    SUPABASE_SERVICE_ROLE_KEY = SUPABASE_SECRET_KEY
    SUPABASE_AUTH_ENABLED = os.getenv("SUPABASE_AUTH_ENABLED", "false").lower() == "true"
    SUPABASE_EMAIL_REDIRECT_URL = os.getenv(
        "SUPABASE_EMAIL_REDIRECT_URL",
        "http://127.0.0.1:5000/auth/callback" if ENV == "development" else "",
    )
    SUPABASE_STORAGE_BUCKET = os.getenv("SUPABASE_STORAGE_BUCKET", "career-documents")
    SESSION_TYPE = "redis" if os.getenv("SESSION_REDIS_URL") else "cachelib"
    SESSION_REDIS = Redis.from_url(os.getenv("SESSION_REDIS_URL")) if os.getenv("SESSION_REDIS_URL") else None
    SESSION_FILE_DIR = os.getenv("SESSION_FILE_DIR", str(BASE_DIR / "instance" / "sessions"))
    SESSION_CACHELIB = FileSystemCache(SESSION_FILE_DIR, threshold=500, mode=0o600)
    SESSION_PERMANENT = True
    SESSION_KEY_PREFIX = "careerpath:"
    AUTH_SESSION_VALIDATION = True


class DevelopmentConfig(Config):
    DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"


class TestingConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = os.getenv("WTF_CSRF_ENABLED", "true").lower() == "true"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    UPLOAD_FOLDER = str(BASE_DIR / "instance" / "test_uploads")
    MAX_CONTENT_LENGTH = 1024 * 1024
    RATELIMIT_ENABLED = False
    SUPABASE_AUTH_ENABLED = False
    SQLALCHEMY_ENGINE_OPTIONS = {}
    SESSION_TYPE = "cachelib"
    AUTH_SESSION_VALIDATION = False


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True


def get_config():
    env = os.getenv("FLASK_ENV", "development").lower()
    if env == "production":
        return ProductionConfig
    if env == "testing":
        return TestingConfig
    return DevelopmentConfig
