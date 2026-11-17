from app.extensions import db
from app.models import Phase, Project, ProjectMember, User
from tests.conftest import csrf_token, login


def create_project(client, admin):
    login(client, admin.email, "StrongPass123!")
    token = csrf_token(client, "/projects/new")
    response = client.post(
        "/projects/new",
        data={
            "csrf_token": token,
            "name": "Plataforma de seguimiento",
            "description": "Proyecto de prueba",
            "objectives": "Organizar entregables",
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
            "base_budget": "12500.00",
            "status": "active",
        },
    )
    assert response.status_code == 302
    return db.session.scalar(db.select(Project).where(Project.name == "Plataforma de seguimiento"))


def logout(client):
    token = csrf_token(client, "/")
    client.post("/logout", data={"csrf_token": token})


def test_admin_can_create_project_and_phase(client, admin):
    project = create_project(client, admin)
    assert project.base_budget == 12500
    assert project.status == "active"

    token = csrf_token(client, f"/projects/{project.id}")
    response = client.post(
        f"/projects/{project.id}/phases",
        data={
            "csrf_token": token,
            "name": "Análisis",
            "description": "Definir alcance",
            "position": "1",
            "start_date": "2026-01-01",
            "end_date": "2026-02-01",
        },
    )
    assert response.status_code == 302
    phase = db.session.scalar(db.select(Phase).where(Phase.project_id == project.id))
    assert phase.name == "Análisis"
    assert client.get(f"/projects/{project.id}").status_code == 200


def test_project_rejects_end_date_before_start_date(client, admin):
    login(client, admin.email, "StrongPass123!")
    response = client.post(
        "/projects/new",
        data={
            "csrf_token": csrf_token(client, "/projects/new"),
            "name": "Fechas inválidas",
            "description": "",
            "objectives": "",
            "start_date": "2026-12-31",
            "end_date": "2026-01-01",
            "base_budget": "100",
            "status": "planning",
        },
    )
    assert response.status_code == 200
    assert "La fecha final debe ser igual o posterior al inicio".encode() in response.data
    assert db.session.scalar(db.select(Project).where(Project.name == "Fechas inválidas")) is None


def test_project_manager_can_manage_phases_but_client_is_read_only(client, admin, make_user):
    project = create_project(client, admin)
    manager = make_user(email="manager@example.com")
    client_user = make_user(email="client@example.com", role="client")
    db.session.add_all(
        [
            ProjectMember(project_id=project.id, user_id=manager.id, project_role="project_manager"),
            ProjectMember(project_id=project.id, user_id=client_user.id, project_role="client"),
        ]
    )
    db.session.commit()

    logout(client)
    login(client, manager.email)
    token = csrf_token(client, f"/projects/{project.id}")
    response = client.post(
        f"/projects/{project.id}/phases",
        data={"csrf_token": token, "name": "Diseño", "position": "1"},
    )
    assert response.status_code == 302

    logout(client)
    login(client, client_user.email)
    assert client.get(f"/projects/{project.id}").status_code == 200
    token = csrf_token(client, f"/projects/{project.id}")
    response = client.post(
        f"/projects/{project.id}/phases",
        data={"csrf_token": token, "name": "No autorizado", "position": "2"},
    )
    assert response.status_code == 403
    assert db.session.scalar(
        db.select(Phase).where(Phase.name == "No autorizado")
    ) is None


def test_project_membership_is_required_to_view_project(client, admin, make_user):
    project = create_project(client, admin)
    outsider = make_user(email="outsider@example.com")
    logout(client)
    login(client, outsider.email)
    assert client.get(f"/projects/{project.id}").status_code == 404


def test_client_account_cannot_be_assigned_project_manager(client, admin, make_user):
    project = create_project(client, admin)
    stakeholder = make_user(email="stakeholder@example.com", role="client")
    token = csrf_token(client, f"/projects/{project.id}")
    response = client.post(
        f"/projects/{project.id}/members",
        data={
            "csrf_token": token,
            "user_id": stakeholder.id,
            "project_role": "project_manager",
        },
    )
    assert response.status_code == 302
    assert db.session.scalar(
        db.select(ProjectMember).where(
            ProjectMember.project_id == project.id, ProjectMember.user_id == stakeholder.id
        )
    ) is None


def test_project_team_assignment_uses_unique_members(client, app, admin, make_user):
    project = create_project(client, admin)
    developer = make_user(email="developer@example.com")
    token = csrf_token(client, f"/projects/{project.id}")
    response = client.post(
        f"/projects/{project.id}/members",
        data={"csrf_token": token, "user_id": developer.id, "project_role": "developer"},
    )
    assert response.status_code == 302
    with app.app_context():
        assert db.session.scalar(
            db.select(db.func.count())
            .select_from(ProjectMember)
            .where(ProjectMember.project_id == project.id, ProjectMember.user_id == developer.id)
        ) == 1
