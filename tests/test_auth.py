from tests import conftest
from tests.conftest import login


def test_login_page(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert b"DevProject Manager" in response.data


def test_private_page_requires_login(client):
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_successful_login_access_dashboard(client, make_user):
    make_user()
    response = login(client)
    assert response.status_code == 302
    response = client.get("/")
    assert response.status_code == 200
    assert b"Bienvenido" in response.data


def test_local_domain_email_is_accepted(client, make_user):
    make_user(email="admin@devproject.local")
    response = login(client, email="ADMIN@DEVPROJECT.LOCAL")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")


def test_empty_email_is_rejected(client):
    response = client.post(
        "/login",
        data={
            "email": "",
            "password": "StrongPass123!",
            "csrf_token": conftest.csrf_token(client),
        },
    )
    assert response.status_code == 200
    assert b"This field is required" in response.data or b"Obligatorio" in response.data


def test_wrong_password_is_rejected(client, make_user):
    make_user()
    response = login(client, password="WrongPassword!23")
    assert response.status_code == 200
    assert b"Correo o contrase" in response.data


def test_wrong_credentials_are_rejected_for_local_domain(client, make_user):
    make_user(email="admin@devproject.local")
    response = login(client, email="admin@devproject.local", password="IncorrectPass123!")
    assert response.status_code == 200
    assert b"Correo o contrase" in response.data
    assert b"Ingresa un correo v" not in response.data


def test_inactive_user_cannot_login(client, make_user):
    make_user(active=False)
    response = login(client)
    assert response.status_code == 200
    assert b"Correo o contrase" in response.data
    with client.session_transaction() as session_data:
        assert "_user_id" not in session_data


def test_logout_invalidates_session(client, make_user):
    make_user()
    login(client)
    csrf_token = conftest.csrf_token(client, "/")
    response = client.post("/logout", data={"csrf_token": csrf_token}, follow_redirects=True)
    assert response.status_code == 200
    assert b"Sesi" in response.data
    assert client.get("/", follow_redirects=False).status_code == 302
