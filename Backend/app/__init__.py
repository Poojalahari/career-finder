import logging
import uuid
from pathlib import Path

from flask import Flask, g, jsonify, redirect, render_template, request, url_for
from werkzeug.exceptions import RequestEntityTooLarge
from flask_login import current_user
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from config import configured, get_config

from .extensions import csrf, db, limiter, login_manager, migrate, server_session


def create_app(config_object=None):
    project_root = Path(__file__).resolve().parents[2]
    app = Flask(
        __name__,
        instance_relative_config=True,
        instance_path=str(project_root / "Backend" / "instance"),
        template_folder=str(project_root / "frontend" / "templates"),
        static_folder=str(project_root / "frontend" / "static"),
    )
    app.config.from_object(config_object or get_config())
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    app.logger.setLevel(logging.INFO)
    app.logger.info("Supabase URL configured: %s", "yes" if configured(app.config.get("SUPABASE_URL")) else "no")
    app.logger.info("Supabase public key configured: %s", "yes" if configured(app.config.get("SUPABASE_PUBLISHABLE_KEY")) else "no")
    app.logger.info("Supabase privileged key configured: %s", "yes" if configured(app.config.get("SUPABASE_SECRET_KEY")) else "no")
    validate_production_config(app)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    if app.config.get("SESSION_TYPE") == "cachelib":
        Path(app.config["SESSION_FILE_DIR"]).mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    login_manager.init_app(app)
    limiter.init_app(app)
    server_session.init_app(app)

    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "info"
    login_manager.session_protection = None if app.config.get("TESTING") else "strong"

    register_auth_session_restoration(app)
    register_blueprints(app)
    register_handlers(app)
    register_security_headers(app)

    return app


def validate_production_config(app):
    if app.config.get("TESTING") or app.config.get("DEBUG"):
        return
    if app.config.get("ENV") != "production" and app.config.get("FLASK_ENV") != "production":
        return
    required = ("SUPABASE_URL", "SUPABASE_PUBLISHABLE_KEY", "SUPABASE_SECRET_KEY", "DATABASE_URL")
    missing = [name for name in required if not configured(app.config.get(name))]
    if not app.config.get("SUPABASE_AUTH_ENABLED"):
        missing.append("SUPABASE_AUTH_ENABLED=true")
    secret_key = str(app.config.get("SECRET_KEY", ""))
    if len(secret_key) < 32 or not configured(secret_key):
        missing.append("FLASK_SECRET_KEY")
    if not str(app.config.get("SQLALCHEMY_DATABASE_URI", "")).startswith("postgresql+"):
        missing.append("DATABASE_URL (PostgreSQL required)")
    if missing:
        raise RuntimeError(f"Missing production configuration: {', '.join(sorted(set(missing)))}")


def register_auth_session_restoration(app):
    from .auth.services import restore_authenticated_session

    @app.before_request
    def restore_supabase_session():
        restore_authenticated_session()


def register_blueprints(app):
    from .auth.routes import bp as auth_bp
    from .ats.routes import bp as ats_bp
    from .career.routes import bp as career_bp
    from .analytics.routes import bp as analytics_bp
    from .admin.routes import bp as admin_bp
    from .chatbot.routes import bp as chatbot_bp
    from .dashboard.routes import bp as dashboard_bp
    from .growth.routes import bp as growth_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(career_bp)
    app.register_blueprint(ats_bp)
    app.register_blueprint(growth_bp)
    app.register_blueprint(chatbot_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(admin_bp)

    @app.get("/")
    def home():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard.index"))
        return render_template("landing.html")

    @app.get("/health")
    def health():
        from .services import supabase_auth

        try:
            db.session.execute(text("SELECT 1"))
        except SQLAlchemyError:
            db.session.rollback()
            return jsonify({"status": "unavailable", "application": "CareerPath ATS", "database": "disconnected"}), 503
        return jsonify({
            "status": "ok",
            "application": "CareerPath ATS",
            "version": "current-build",
            "database": "connected",
            "supabase_auth": "configured" if supabase_auth.enabled() else "disabled",
        }), 200


def register_handlers(app):
    @app.before_request
    def add_request_id():
        g.request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

    @app.errorhandler(403)
    def forbidden(error):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(429)
    def too_many(error):
        return render_template("errors/429.html"), 429

    @app.errorhandler(RequestEntityTooLarge)
    def upload_too_large(error):
        from .ats.forms import ResumeScanForm

        limit_mb = app.config["MAX_CONTENT_LENGTH"] // 1024 // 1024
        if request.accept_mimetypes.best == "application/json":
            return jsonify({"error": f"PDF size must be {limit_mb} MB or less."}), 413
        return render_template("ats/scan.html", form=ResumeScanForm(formdata=None),
                               upload_error=f"PDF size must be {limit_mb} MB or less."), 413

    @app.errorhandler(500)
    def server_error(error):
        db.session.rollback()
        app.logger.exception("Unhandled request failure id=%s", getattr(g, "request_id", "-"))
        return render_template("errors/500.html"), 500


def register_security_headers(app):
    @app.after_request
    def headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data:; style-src 'self'; "
            "script-src 'self'; font-src 'self'; base-uri 'self'; frame-ancestors 'none'"
        )
        response.headers["X-Request-ID"] = getattr(g, "request_id", "-")
        return response
