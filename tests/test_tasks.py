from datetime import date
from decimal import Decimal

from app.extensions import db
from app.models import Phase, Project, ProjectMember, Task, WorkLog
from tests.conftest import csrf_token, login
from tests.test_projects import create_project, logout


def project_with_task(client, admin, make_user):
    project = create_project(client, admin)
    developer = make_user(email="task-dev@example.com")
    phase = Phase(project_id=project.id, name="Desarrollo", position=1)
    db.session.add(phase)
    db.session.flush()
    db.session.add(
        ProjectMember(project_id=project.id, user_id=developer.id, project_role="developer")
    )
    db.session.commit()
    token = csrf_token(client, f"/projects/{project.id}/tasks/new")
    response = client.post(
        f"/projects/{project.id}/tasks/new",
        data={
            "csrf_token": token,
            "phase_id": phase.id,
            "title": "Implementar autenticación",
            "description": "Conectar login y sesión",
            "priority": "high",
            "assignee_user_id": developer.id,
            "planned_hours": "12.5",
            "status": "todo",
        },
    )
    assert response.status_code == 302
    task = db.session.scalar(db.select(Task).where(Task.title == "Implementar autenticación"))
    return project, phase, developer, task


def test_task_crud_and_phase_assignment(client, admin, make_user):
    project, phase, developer, task = project_with_task(client, admin, make_user)
    assert task.project_id == project.id
    assert task.phase_id == phase.id
    assert task.assignee_user_id == developer.id
    assert task.planned_hours == Decimal("12.50")

    token = csrf_token(client, f"/projects/{project.id}/tasks/{task.id}/edit")
    response = client.post(
        f"/projects/{project.id}/tasks/{task.id}/edit",
        data={
            "csrf_token": token,
            "phase_id": phase.id,
            "title": "Implementar login seguro",
            "description": "",
            "priority": "urgent",
            "assignee_user_id": developer.id,
            "planned_hours": "14",
            "status": "in_progress",
        },
    )
    assert response.status_code == 302
    assert task.title == "Implementar login seguro"
    assert task.status == "in_progress"

    token = csrf_token(client, f"/projects/{project.id}/tasks/{task.id}")
    response = client.post(
        f"/projects/{project.id}/tasks/{task.id}/delete",
        data={"csrf_token": token},
    )
    assert response.status_code == 302
    assert db.session.get(Task, task.id) is None


def test_developer_records_actual_hours_and_updates_assigned_task(
    client, admin, make_user
):
    project, _, developer, task = project_with_task(client, admin, make_user)
    logout(client)
    login(client, developer.email)

    token = csrf_token(client, f"/projects/{project.id}/tasks/{task.id}")
    response = client.post(
        f"/projects/{project.id}/tasks/{task.id}/logs",
        data={
            "csrf_token": token,
            "hours": "3.75",
            "work_date": "2026-03-02",
            "notes": "Implementación y pruebas",
        },
    )
    assert response.status_code == 302
    work_log = db.session.scalar(db.select(WorkLog).where(WorkLog.task_id == task.id))
    assert work_log.hours == Decimal("3.75")
    assert work_log.work_date == date(2026, 3, 2)

    token = csrf_token(client, f"/projects/{project.id}/tasks/{task.id}")
    response = client.post(
        f"/projects/{project.id}/tasks/{task.id}/status",
        data={"csrf_token": token, "status": "review"},
    )
    assert response.status_code == 302
    assert task.status == "review"
    detail = client.get(f"/projects/{project.id}/tasks/{task.id}")
    assert b"3.75" in detail.data
    assert b"12.50" in detail.data
    project_detail = client.get(f"/projects/{project.id}")
    assert b"Implementar autenticaci" in project_detail.data
    assert b"3.75" in project_detail.data


def test_task_board_filters_by_assignee_and_status(client, admin, make_user):
    project, _, developer, _ = project_with_task(client, admin, make_user)
    logout(client)
    login(client, developer.email)
    response = client.get(
        f"/projects/{project.id}/tasks?assignee={developer.id}&status=todo"
    )
    assert response.status_code == 200
    assert b"Implementar autenticaci" in response.data
    response = client.get(
        f"/projects/{project.id}/tasks?assignee={developer.id}&status=done"
    )
    assert response.status_code == 200
    assert b"Implementar autenticaci" not in response.data


def test_client_cannot_change_task_or_log_time(client, admin, make_user):
    project, _, _, task = project_with_task(client, admin, make_user)
    client_user = make_user(email="task-client@example.com", role="client")
    db.session.add(
        ProjectMember(project_id=project.id, user_id=client_user.id, project_role="client")
    )
    db.session.commit()
    logout(client)
    login(client, client_user.email)

    token = csrf_token(client, f"/projects/{project.id}/tasks/{task.id}")
    response = client.post(
        f"/projects/{project.id}/tasks/{task.id}/status",
        data={"csrf_token": token, "status": "done"},
    )
    assert response.status_code == 403
    token = csrf_token(client, f"/projects/{project.id}/tasks/{task.id}")
    response = client.post(
        f"/projects/{project.id}/tasks/{task.id}/logs",
        data={"csrf_token": token, "hours": "2", "work_date": "2026-03-02"},
    )
    assert response.status_code == 403
    assert not task.work_logs


def test_task_rejects_phase_from_another_project(client, admin, make_user):
    project, _, developer, _ = project_with_task(client, admin, make_user)
    other_project = Project(
        name="Otro proyecto",
        description="",
        objectives="",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        base_budget=100,
        status="planning",
    )
    db.session.add(other_project)
    db.session.flush()
    other_phase = Phase(project_id=other_project.id, name="Otra fase", position=1)
    db.session.add(other_phase)
    db.session.commit()
    token = csrf_token(client, f"/projects/{project.id}/tasks/new")
    response = client.post(
        f"/projects/{project.id}/tasks/new",
        data={
            "csrf_token": token,
            "phase_id": other_phase.id,
            "title": "Fase no válida",
            "description": "",
            "priority": "low",
            "assignee_user_id": developer.id,
            "planned_hours": "1",
            "status": "todo",
        },
    )
    assert response.status_code == 200
    assert db.session.scalar(db.select(Task).where(Task.title == "Fase no válida")) is None
    assert other_phase.project_id != project.id
