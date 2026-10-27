import re

import pytest

from app import create_app
from app.extensions import db
from app.models import User


@pytest.fixture
def app():
    app = create_app({
        "TESTING": True,
        "SECRET_KEY": "test-only-secret-not-for-production",
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": True,
    })
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def make_user(app):
    def _make(full_name="Test User", email="test@example.com", password="StrongPass123!", role="developer", active=True):
        user = User(full_name=full_name, email=email, role=role, is_active=active)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user
    return _make


@pytest.fixture
def admin(make_user):
    return make_user(full_name="Admin Test", email="admin@example.com", role="admin")


def csrf_token(client, path="/login"):
    response = client.get(path)
    assert response.status_code == 200
    match = re.search(rb'name="csrf_token"[^>]*value="([^"]+)"', response.data)
    assert match is not None
    return match.group(1).decode()


def login(client, email="test@example.com", password="StrongPass123!"):
    token = csrf_token(client)
    return client.post(
        "/login",
        data={"email": email, "password": password, "csrf_token": token},
        follow_redirects=False,
    )
