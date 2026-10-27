from flask import flash, redirect, render_template, url_for
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError

from app.decorators import roles_required
from app.extensions import db
from app.models import User
from app.users import users_bp
from app.users.forms import CreateUserForm
from app.validation import normalize_email


@users_bp.route("/")
@login_required
@roles_required("admin")
def index():
    users = db.session.scalars(db.select(User).order_by(User.created_at.desc())).all()
    form = CreateUserForm()
    return render_template("users/index.html", users=users, form=form)


@users_bp.route("/create", methods=["POST"])
@login_required
@roles_required("admin")
def create():
    form = CreateUserForm()
    if not form.validate_on_submit():
        users = db.session.scalars(db.select(User).order_by(User.created_at.desc())).all()
        return render_template("users/index.html", users=users, form=form), 400

    email = normalize_email(form.email.data)
    if db.session.scalar(db.select(User).where(db.func.lower(User.email) == email)):
        flash("Ya existe un usuario con ese correo electrónico.", "danger")
        users = db.session.scalars(db.select(User).order_by(User.created_at.desc())).all()
        return render_template("users/index.html", users=users, form=form), 400

    user = User(
        full_name=form.full_name.data.strip(),
        email=email,
        role=form.role.data,
        is_active=form.is_active.data,
    )
    user.set_password(form.password.data)
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash("Ya existe un usuario con ese correo electrónico.", "danger")
        users = db.session.scalars(db.select(User).order_by(User.created_at.desc())).all()
        return render_template("users/index.html", users=users, form=form), 400

    flash("Usuario registrado correctamente.", "success")
    return redirect(url_for("users.index"))


@users_bp.route("/<int:user_id>/toggle-active", methods=["POST"])
@login_required
@roles_required("admin")
def toggle_active(user_id):
    user = db.session.get(User, user_id)
    if user is None:
        return render_template("errors/404.html"), 404
    if user.id == current_user.id:
        flash("No puedes activar o desactivar tu propia cuenta.", "danger")
        return redirect(url_for("users.index"))

    active_admin_count = db.session.scalar(
        db.select(db.func.count()).select_from(User).where(User.role == "admin", User.is_active)
    )
    if user.role == "admin" and user.is_active and active_admin_count == 1:
        flash("Debe existir al menos un administrador activo.", "danger")
        return redirect(url_for("users.index"))

    user.is_active = not user.is_active
    db.session.commit()
    state = "activado" if user.is_active else "desactivado"
    flash(f"Usuario {state} correctamente.", "success")
    return redirect(url_for("users.index"))
