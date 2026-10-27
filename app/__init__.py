import os
from flask import Flask, render_template

from app.extensions import db, login_manager, csrf


def create_app(config_overrides=None):
    app = Flask(__name__, instance_relative_config=True)

    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY"),
        SQLALCHEMY_DATABASE_URI=os.environ.get(
            "DATABASE_URL", "sqlite:///{instance_path}/devproject.db"
        ).replace("{instance_path}", app.instance_path),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        WTF_CSRF_ENABLED=True,
        REMEMBER_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE", "false").lower() == "true",
        PERMANENT_SESSION_LIFETIME=3600,
    )

    app.config.from_pyfile("config.py", silent=True)
    if config_overrides:
        app.config.update(config_overrides)

    if not app.config.get("SECRET_KEY"):
        raise RuntimeError(
            "SECRET_KEY no está configurada. Define una clave segura mediante la variable de entorno SECRET_KEY."
        )

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    login_manager.login_view = "auth.login"
    login_manager.login_message = "Debes iniciar sesión para acceder a esta página."
    login_manager.login_message_category = "warning"

    from app.auth import auth_bp
    from app.users import users_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(users_bp)

    from app.cli import register_cli

    register_cli(app)

    @app.errorhandler(403)
    def forbidden(error):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(error):
        db.session.rollback()
        return render_template("errors/500.html"), 500

    return app
