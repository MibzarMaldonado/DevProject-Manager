from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from urllib.parse import urljoin, urlparse

from app.auth import auth_bp
from app.auth.forms import LoginForm
from app.extensions import db
from app.models import User
from app.validation import normalize_email


def is_safe_next_url(target):
    if not target:
        return False
    host_url = urlparse(request.host_url)
    redirect_url = urlparse(urljoin(request.host_url, target))
    return redirect_url.scheme in ("http", "https") and redirect_url.netloc == host_url.netloc


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("auth.dashboard"))
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(
            db.select(User).where(db.func.lower(User.email) == normalize_email(form.email.data))
        )
        if user is None or not user.is_active or not user.check_password(form.password.data):
            flash("Correo o contraseña incorrectos.", "danger")
        else:
            login_user(user)
            next_url = request.args.get("next")
            return redirect(next_url if is_safe_next_url(next_url) else url_for("auth.dashboard"))
    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("Sesión cerrada correctamente.", "success")
    return redirect(url_for("auth.login"))


@auth_bp.route("/")
@login_required
def dashboard():
    return render_template("dashboard.html")
