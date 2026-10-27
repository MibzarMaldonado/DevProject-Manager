from app import create_app
from app.extensions import db
from app.models import User


def make_cli_app():
    app = create_app({
        "TESTING": True,
        "SECRET_KEY": "cli-test-secret",
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    })
    with app.app_context():
        db.create_all()
    return app


def test_init_admin_creates_first_admin(monkeypatch):
    app = make_cli_app()
    passwords = iter(["SecureAdmin123!", "SecureAdmin123!"])
    monkeypatch.setattr("app.cli.getpass.getpass", lambda prompt: next(passwords))

    result = app.test_cli_runner().invoke(args=["init-admin"], input="Admin Test\nadmin@example.com\n")

    assert result.exit_code == 0
    assert "Administrador creado correctamente" in result.output
    with app.app_context():
        user = db.session.scalar(db.select(User).where(User.email == "admin@example.com"))
        assert user.role == "admin"
        assert user.check_password("SecureAdmin123!")


def test_reset_admin_password_updates_only_hash(monkeypatch):
    app = make_cli_app()
    with app.app_context():
        admin = User(full_name="Existing Admin", email="admin@example.com", role="admin")
        admin.set_password("OriginalPass123!")
        old_admin_hash = admin.password_hash
        developer = User(full_name="Other User", email="developer@example.com", role="developer")
        developer.set_password("DeveloperPass123!")
        old_developer_hash = developer.password_hash
        db.session.add_all([admin, developer])
        db.session.commit()

    passwords = iter(["ReplacementPass123!", "ReplacementPass123!"])
    monkeypatch.setattr("app.cli.getpass.getpass", lambda prompt: next(passwords))
    result = app.test_cli_runner().invoke(
        args=["reset-admin-password"],
        input="admin@example.com\ny\n",
    )

    assert result.exit_code == 0
    assert "restablecida correctamente" in result.output
    with app.app_context():
        admin = db.session.scalar(db.select(User).where(User.email == "admin@example.com"))
        assert admin.password_hash != old_admin_hash
        assert admin.check_password("ReplacementPass123!")
        assert admin.role == "admin"
        assert admin.is_active
        developer = db.session.scalar(db.select(User).where(User.email == "developer@example.com"))
        assert developer.password_hash == old_developer_hash
        assert developer.check_password("DeveloperPass123!")


def test_reset_admin_password_requires_exact_confirmation(monkeypatch):
    app = make_cli_app()
    with app.app_context():
        admin = User(full_name="Existing Admin", email="admin@example.com", role="admin")
        admin.set_password("OriginalPass123!")
        old_hash = admin.password_hash
        db.session.add(admin)
        db.session.commit()
        admin_id = admin.id

    monkeypatch.setattr("app.cli.getpass.getpass", lambda prompt: "unused")
    result = app.test_cli_runner().invoke(
        args=["reset-admin-password"],
        input="wrong@example.com\ny\n",
    )

    assert result.exit_code != 0
    assert "no corresponde" in result.output
    with app.app_context():
        assert db.session.get(User, admin_id).password_hash == old_hash


def test_init_admin_refuses_second_admin(monkeypatch):
    app = make_cli_app()
    with app.app_context():
        admin = User(full_name="Existing Admin", email="existing@example.com", role="admin")
        admin.set_password("SecureAdmin123!")
        db.session.add(admin)
        db.session.commit()

    monkeypatch.setattr("app.cli.getpass.getpass", lambda prompt: "unused")
    result = app.test_cli_runner().invoke(args=["init-admin"])

    assert result.exit_code != 0
    assert "Ya existe un administrador" in result.output
    with app.app_context():
        assert db.session.scalar(db.select(db.func.count()).select_from(User)) == 1
