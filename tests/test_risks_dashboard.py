from decimal import Decimal

from app.extensions import db
from app.models import ProjectDocument, ProjectMember, Risk
from tests.conftest import csrf_token, login
from tests.test_projects import logout
from tests.test_tasks import project_with_task


def test_risk_severity_is_calculated_and_crud_is_project_scoped(client, admin, make_user):
    project, _, _, _ = project_with_task(client, admin, make_user)
    token = csrf_token(client, f"/projects/{project.id}/risks-documents")
    response = client.post(
        f"/projects/{project.id}/risks",
        data={
            "csrf_token": token,
            "title": "Dependencia externa inestable",
            "description": "El servicio puede interrumpirse",
            "category": "technical",
            "probability": "4",
            "impact": "5",
            "mitigation": "Agregar reintentos y monitoreo",
        },
    )
    assert response.status_code == 302
    risk = db.session.scalar(db.select(Risk).where(Risk.project_id == project.id))
    assert risk.severity == 20
    assert risk.severity_label == "Crítico"

    token = csrf_token(client, f"/projects/{project.id}/risks-documents")
    response = client.post(
        f"/projects/{project.id}/risks/{risk.id}/edit",
        data={
            "csrf_token": token,
            "title": "Dependencia controlada",
            "description": "",
            "category": "technical",
            "probability": "1",
            "impact": "1",
            "mitigation": "Monitorear el servicio",
        },
    )
    assert response.status_code == 302
    assert risk.severity == 1
    assert risk.severity_label == "Bajo"

    token = csrf_token(client, f"/projects/{project.id}/risks-documents")
    response = client.post(
        f"/projects/{project.id}/risks/{risk.id}/delete",
        data={"csrf_token": token},
    )
    assert response.status_code == 302
    assert db.session.get(Risk, risk.id) is None


def test_document_links_only_allow_http_or_https(client, admin, make_user):
    project, _, _, _ = project_with_task(client, admin, make_user)
    token = csrf_token(client, f"/projects/{project.id}/risks-documents")
    response = client.post(
        f"/projects/{project.id}/documents",
        data={
            "csrf_token": token,
            "title": "Arquitectura",
            "document_type": "architecture",
            "url": "https://docs.example.com/architecture",
            "description": "Diagrama de componentes",
        },
    )
    assert response.status_code == 302
    document = db.session.scalar(
        db.select(ProjectDocument).where(ProjectDocument.project_id == project.id)
    )
    assert document.url == "https://docs.example.com/architecture"

    token = csrf_token(client, f"/projects/{project.id}/risks-documents")
    client.post(
        f"/projects/{project.id}/documents",
        data={
            "csrf_token": token,
            "title": "Enlace no seguro",
            "document_type": "other",
            "url": "javascript:alert(1)",
            "description": "",
        },
    )
    assert db.session.scalar(
        db.select(db.func.count())
        .select_from(ProjectDocument)
        .where(ProjectDocument.project_id == project.id)
    ) == 1


def test_dashboard_metrics_and_pdf_report_match_recorded_work(client, admin, make_user):
    project, _, developer, task = project_with_task(client, admin, make_user)
    logout(client)
    login(client, developer.email)
    token = csrf_token(client, f"/projects/{project.id}/tasks/{task.id}")
    client.post(
        f"/projects/{project.id}/tasks/{task.id}/logs",
        data={
            "csrf_token": token,
            "hours": "3.75",
            "work_date": "2026-03-02",
            "notes": "Trabajo realizado",
        },
    )
    token = csrf_token(client, f"/projects/{project.id}/tasks/{task.id}")
    client.post(
        f"/projects/{project.id}/tasks/{task.id}/status",
        data={"csrf_token": token, "status": "done"},
    )
    assert task.hourly_rate == Decimal("40.00")

    dashboard = client.get(f"/projects/{project.id}/dashboard")
    assert dashboard.status_code == 200
    assert b"100%" in dashboard.data
    assert b"3.75" in dashboard.data
    assert b"150.00" in dashboard.data
    assert b"12350.00" in dashboard.data

    report = client.get(f"/projects/{project.id}/report.pdf")
    assert report.status_code == 200
    assert report.mimetype == "application/pdf"
    assert report.data.startswith(b"%PDF-")
    assert len(report.data) > 1000


def test_client_can_read_but_cannot_manage_risks_or_documents(client, admin, make_user):
    project, _, _, _ = project_with_task(client, admin, make_user)
    stakeholder = make_user(email="read-only@example.com", role="client")
    db.session.add(
        ProjectMember(project_id=project.id, user_id=stakeholder.id, project_role="client")
    )
    db.session.commit()
    logout(client)
    login(client, stakeholder.email)
    assert client.get(f"/projects/{project.id}/risks-documents").status_code == 200

    token = csrf_token(client, f"/projects/{project.id}/risks-documents")
    response = client.post(
        f"/projects/{project.id}/risks",
        data={
            "csrf_token": token,
            "title": "No autorizado",
            "description": "",
            "category": "other",
            "probability": "2",
            "impact": "2",
            "mitigation": "Ninguna",
        },
    )
    assert response.status_code == 403
    assert db.session.scalar(db.select(Risk).where(Risk.title == "No autorizado")) is None
