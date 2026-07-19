from urllib.parse import urlsplit

from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, logout_user

from app.extensions import limiter

from app.services import supabase_auth

from .forms import ForgotPasswordForm, LoginForm, RegisterForm, ResetPasswordForm
from .services import authenticate, complete_email_confirmation, complete_implicit_confirmation, complete_recovery, register_user

bp = Blueprint("auth", __name__)


@bp.route("/register", methods=["GET", "POST"])
@limiter.limit("8 per minute")
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))
    form = RegisterForm()
    if form.validate_on_submit():
        normalized_email = form.email.data.strip().lower()
        user, error = register_user(form.full_name.data, normalized_email, form.password.data)
        if error:
            flash(error["message"], "error")
            if error["code"] == "account_exists":
                return redirect(url_for("auth.login", email=normalized_email, reason="account-exists"))
        elif user.get("authenticated"):
            flash("Account created successfully. Opening your dashboard…", "success")
            return redirect(url_for("dashboard.index"))
        else:
            flash("Account created successfully. A verification link was sent to your email.", "success")
            return redirect(url_for("auth.login"))
    return render_template("auth/register.html", form=form)


@bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))
    form = LoginForm()
    if request.method == "GET":
        form.email.data = request.args.get("email", "").strip().lower()
        if request.args.get("reason") == "account-exists":
            flash("An account already exists with this email. Enter your password to log in.", "info")
    if form.validate_on_submit():
        authenticated, error = authenticate(form.email.data, form.password.data, form.remember.data)
        if authenticated:
            flash("Welcome back.", "success")
            next_url = request.args.get("next", "")
            if next_url and not urlsplit(next_url).netloc and next_url.startswith("/"):
                return redirect(next_url)
            if current_user.role in {"super_admin", "admin"}:
                return redirect(url_for("admin.index"))
            return redirect(url_for("dashboard.index"))
        flash(error or "Invalid email or password.", "error")
    return render_template("auth/login.html", form=form)


@bp.post("/logout")
@login_required
def logout():
    access_token = session.get("supabase_access_token")
    if access_token:
        try:
            supabase_auth.sign_out(access_token)
        except supabase_auth.SupabaseAuthError:
            pass
    logout_user()
    session.clear()
    flash("You have been signed out.", "info")
    return redirect(url_for("auth.login"))


@bp.route("/forgot-password", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def forgot_password():
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        try:
            supabase_auth.request_password_reset(form.email.data.strip().lower())
        except supabase_auth.SupabaseAuthError:
            current_app.logger.warning("Password reset request could not be delivered")
        flash("If that account exists, a password reset link has been sent.", "info")
        return redirect(url_for("auth.login"))
    return render_template("auth/forgot_password.html", form=form)


@bp.get("/auth/callback")
def callback():
    token_hash = request.args.get("token_hash", "")
    callback_type = request.args.get("type", "")
    if token_hash and callback_type == "recovery":
        authenticated, error = complete_recovery(token_hash)
        destination = "auth.reset_password"
    elif token_hash and callback_type in {"email", "signup"}:
        authenticated, error = complete_email_confirmation(token_hash)
        destination = "dashboard.index"
    else:
        return render_template("auth/callback.html")
    if not authenticated:
        flash(error, "error")
        return redirect(url_for("auth.login"))
    flash("Email verified successfully. Welcome to your dashboard.", "success")
    return redirect(url_for(destination))


@bp.post("/auth/session-callback")
@limiter.limit("10 per minute")
def session_callback():
    payload = request.get_json(silent=True) or {}
    authenticated, error = complete_implicit_confirmation(
        str(payload.get("access_token", "")),
        str(payload.get("refresh_token", "")),
    )
    if not authenticated:
        return jsonify({"error": error}), 400
    flash("Email verified successfully. Welcome to your dashboard.", "success")
    return jsonify({"redirect": url_for("dashboard.index")})


@bp.route("/reset-password", methods=["GET", "POST"])
@login_required
def reset_password():
    form = ResetPasswordForm()
    if form.validate_on_submit():
        try:
            supabase_auth.update_password(session.get("supabase_access_token", ""), form.password.data)
        except supabase_auth.SupabaseAuthError:
            flash("The password could not be updated. Request a new reset link.", "error")
        else:
            flash("Password updated successfully.", "success")
            return redirect(url_for("dashboard.index"))
    return render_template("auth/reset_password.html", form=form)
