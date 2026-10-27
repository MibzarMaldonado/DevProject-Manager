from app.extensions import db
from app.models import User
from tests import conftest
from tests.conftest import login


STRONG_PASSWORD = "StrongPass123!"


def post_as_admin(client, admin, path, data):
    login(client, admin.email, STRONG_PASSWORD)
    token = conftest.csrf_token(client, "/users/")
    data = {**data, "csrf_token": token}
    return client.post(path, data=data)


def test_admin_can_list_users(client, admin):
    response = post_as_admin(client, admin, "/users/create", {})
    assert response.status_code == 400
    response = client.get("/users/")
    assert response.status_code == 200
    assert b"admin@example.com" in response.data


def test_admin_can_create_user(client, admin):
    response = post_as_admin(client, admin, "/users/create", {
        "full_name": "New Developer", "email": "DEV@example.com",
        "password": STRONG_PASSWORD, "role": "developer", "is_active": "y",
    })
    assert response.status_code == 302
    user = db.session.scalar(db.select(User).where(User.email == "dev@example.com"))
    assert user is not None


def test_duplicate_email_rejected(client, admin):
    response = post_as_admin(client, admin, "/users/create", {
        "full_name": "Duplicate", "email": "ADMIN@example.com",
        "password": STRONG_PASSWORD, "role": "developer", "is_active": "y",
    })
    assert response.status_code == 400
    assert b"Ya existe un usuario" in response.data


def test_user_registration_still_rejects_local_domain(client, admin):
    response = post_as_admin(client, admin, "/users/create", {
        "full_name": "Local User", "email": "local@devproject.local",
        "password": STRONG_PASSWORD, "role": "developer", "is_active": "y",
    })
    assert response.status_code == 400
    assert b"correo v" in response.data.lower()


def test_weak_password_rejected(client, admin):
    response = post_as_admin(client, admin, "/users/create", {
        "full_name": "Weak", "email": "weak@example.com",
        "password": "weak", "role": "developer", "is_active": "y",
    })
    assert response.status_code == 400
    assert b"al menos 12 caracteres" in response.data


def test_non_admin_forbidden(client, make_user):
    make_user()
    login(client)
    assert client.get("/users/").status_code == 403


def test_csrf_enabled(client):
    response = client.post("/login", data={"email": "nobody@example.com", "password": "anything"})
    assert response.status_code == 400
    assert b"csrf" in response.data.lower() or b"CSRF" in response.data


def test_password_is_hashed(client, admin):
    post_as_admin(client, admin, "/users/create", {
        "full_name": "Hash Test", "email": "hash@example.com",
        "password": STRONG_PASSWORD, "role": "developer", "is_active": "y",
    })
    user = db.session.scalar(db.select(User).where(User.email == "hash@example.com"))
    assert user.password_hash != STRONG_PASSWORD
    assert user.check_password(STRONG_PASSWORD)
