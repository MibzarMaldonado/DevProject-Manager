from decimal import Decimal
from io import BytesIO
from xml.sax.saxutils import escape

from flask import abort, flash, redirect, render_template, send_file, url_for
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError

from app.decorators import roles_required
from app.extensions import db
from app.models import Phase, Project, ProjectMember, User
from app.projects import projects_bp
from app.projects.forms import MemberForm, PhaseForm, ProjectForm
from app.projects.metrics import project_metrics


def project_manager(project):
    if current_user.is_admin():
        return True
    return current_user.role != "client" and any(
        member.user_id == current_user.id and member.project_role == "project_manager"
        for member in project.members
    )


def visible_project_or_404(project_id):
    project = db.session.get(Project, project_id)
    if project is None:
        abort(404)
    if not current_user.is_admin() and not any(
        member.user_id == current_user.id for member in project.members
    ):
        abort(404)
    return project


@projects_bp.route("/")
@login_required
def index():
    if current_user.is_admin():
        projects = db.session.scalars(
            db.select(Project).order_by(Project.created_at.desc())
        ).all()
    else:
        projects = db.session.scalars(
            db.select(Project)
            .join(ProjectMember)
            .where(ProjectMember.user_id == current_user.id)
            .order_by(Project.created_at.desc())
        ).all()
    return render_template("projects/index.html", projects=projects)


@projects_bp.route("/new", methods=["GET", "POST"])
@login_required
@roles_required("admin")
def create():
    form = ProjectForm()
    if form.validate_on_submit():
        project = Project(
            name=form.name.data.strip(),
            description=form.description.data.strip(),
            objectives=form.objectives.data.strip(),
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            base_budget=form.base_budget.data,
            status=form.status.data,
        )
        db.session.add(project)
        db.session.commit()
        flash("Proyecto creado correctamente.", "success")
        return redirect(url_for("projects.detail", project_id=project.id))
    return render_template("projects/form.html", form=form, heading="Nuevo proyecto")


@projects_bp.route("/<int:project_id>")
@login_required
def detail(project_id):
    project = visible_project_or_404(project_id)
    member_form = MemberForm()
    eligible_users = db.session.scalars(
        db.select(User).where(User.is_active).order_by(User.full_name)
    ).all()
    member_form.user_id.choices = [
        (user.id, f"{user.full_name} ({user.email})")
        for user in eligible_users
        if user.id not in {member.user_id for member in project.members}
    ]
    phase_form = PhaseForm()
    return render_template(
        "projects/detail.html",
        project=project,
        member_form=member_form,
        phase_form=phase_form,
        can_manage=project_manager(project),
    )


@projects_bp.route("/<int:project_id>/dashboard")
@login_required
def dashboard(project_id):
    project = visible_project_or_404(project_id)
    metrics = project_metrics(project)
    return render_template(
        "projects/dashboard.html",
        project=project,
        metrics=metrics,
        status_labels={
            "todo": "Por hacer",
            "in_progress": "En progreso",
            "review": "En revisión",
            "done": "Concluidas",
        },
    )


@projects_bp.route("/<int:project_id>/report.pdf")
@login_required
def report(project_id):
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    project = visible_project_or_404(project_id)
    metrics = project_metrics(project)
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=f"Resumen ejecutivo - {project.name}",
        author="DevProject Manager",
    )
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="ReportTitle",
            parent=styles["Title"],
            alignment=TA_CENTER,
            textColor=colors.HexColor("#343a8b"),
            spaceAfter=12,
        )
    )
    styles.add(ParagraphStyle(name="SmallCell", parent=styles["BodyText"], fontSize=8, leading=10))
    story = [
        Paragraph("Resumen ejecutivo del proyecto", styles["ReportTitle"]),
        Paragraph(escape(project.name), styles["Heading2"]),
        Paragraph(escape(project.description or "Sin descripción."), styles["BodyText"]),
        Spacer(1, 8),
    ]
    summary = [
        ["Estado", {"planning": "En planificación", "active": "Activo", "paused": "Pausado", "finished": "Finalizado"}[project.status]],
        ["Periodo", f"{project.start_date:%d/%m/%Y} – {project.end_date:%d/%m/%Y}"],
        ["Avance de tareas", f"{metrics['progress']}% ({metrics['completed_tasks']} de {metrics['task_count']})"],
        ["Horas planificadas / reales", f"{metrics['planned_hours']:.2f} / {metrics['actual_hours']:.2f}"],
        ["Presupuesto base", f"${project.base_budget:,.2f}"],
        ["Costo real registrado", f"${metrics['actual_cost']:,.2f}"],
        ["Balance presupuestal", f"${metrics['budget_balance']:,.2f}"],
        ["Riesgos registrados", str(metrics["risk_count"])],
    ]
    summary_table = Table(
        [["Indicador", "Resultado"]] + summary,
        colWidths=[60 * mm, 110 * mm],
        repeatRows=1,
    )
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#343a8b")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#d5d8e2")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f6fa")]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.extend([summary_table, Spacer(1, 14), Paragraph("Tareas", styles["Heading2"])])
    task_rows = [
        [
            "Tarea",
            "Fase",
            "Responsable",
            "Estado",
            "Plan (h)",
            "Real (h)",
        ]
    ]
    task_status = {"todo": "Por hacer", "in_progress": "En progreso", "review": "En revisión", "done": "Concluida"}
    for task in metrics["tasks"]:
        actual = sum((log.hours for log in task.work_logs), Decimal("0.00"))
        task_rows.append(
            [
                Paragraph(escape(task.title), styles["SmallCell"]),
                Paragraph(escape(task.phase.name), styles["SmallCell"]),
                Paragraph(escape(task.assignee.full_name if task.assignee else "Sin asignar"), styles["SmallCell"]),
                task_status[task.status],
                f"{task.planned_hours:.2f}",
                f"{actual:.2f}",
            ]
        )
    tasks_table = Table(
        task_rows,
        colWidths=[48 * mm, 32 * mm, 35 * mm, 24 * mm, 15 * mm, 15 * mm],
        repeatRows=1,
    )
    tasks_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#343a8b")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#d5d8e2")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f6fa")]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("PADDING", (0, 0), (-1, -1), 5),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(tasks_table)
    document.build(story)
    buffer.seek(0)
    return send_file(
        buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"resumen-proyecto-{project.id}.pdf",
    )


@projects_bp.route("/<int:project_id>/edit", methods=["GET", "POST"])
@login_required
def edit(project_id):
    project = visible_project_or_404(project_id)
    if not project_manager(project):
        abort(403)
    form = ProjectForm(obj=project)
    if form.validate_on_submit():
        form.populate_obj(project)
        project.name = project.name.strip()
        project.description = project.description.strip()
        project.objectives = project.objectives.strip()
        db.session.commit()
        flash("Proyecto actualizado correctamente.", "success")
        return redirect(url_for("projects.detail", project_id=project.id))
    return render_template("projects/form.html", form=form, heading="Editar proyecto")


@projects_bp.route("/<int:project_id>/delete", methods=["POST"])
@login_required
def delete(project_id):
    project = visible_project_or_404(project_id)
    if not project_manager(project):
        abort(403)
    db.session.delete(project)
    db.session.commit()
    flash("Proyecto eliminado.", "success")
    return redirect(url_for("projects.index"))


@projects_bp.route("/<int:project_id>/members", methods=["POST"])
@login_required
def add_member(project_id):
    project = visible_project_or_404(project_id)
    if not project_manager(project):
        abort(403)
    form = MemberForm()
    eligible_users = db.session.scalars(
        db.select(User).where(User.is_active).order_by(User.full_name)
    ).all()
    existing_ids = {member.user_id for member in project.members}
    form.user_id.choices = [
        (user.id, user.full_name) for user in eligible_users if user.id not in existing_ids
    ]
    if form.validate_on_submit():
        assigned_user = db.session.get(User, form.user_id.data)
        if assigned_user is None or (
            assigned_user.role == "client" and form.project_role.data != "client"
        ):
            flash("El perfil Cliente solo puede asignarse como Cliente / Stakeholder.", "danger")
            return redirect(url_for("projects.detail", project_id=project.id))
        member = ProjectMember(
            project_id=project.id, user_id=form.user_id.data, project_role=form.project_role.data
        )
        db.session.add(member)
        try:
            db.session.commit()
            flash("Integrante asignado al proyecto.", "success")
        except IntegrityError:
            db.session.rollback()
            flash("El integrante ya forma parte del proyecto.", "danger")
    else:
        flash("No se pudo asignar el integrante; revisa los datos.", "danger")
    return redirect(url_for("projects.detail", project_id=project.id))


@projects_bp.route("/<int:project_id>/members/<int:member_id>/remove", methods=["POST"])
@login_required
def remove_member(project_id, member_id):
    project = visible_project_or_404(project_id)
    if not project_manager(project):
        abort(403)
    member = db.session.get(ProjectMember, member_id)
    if member is None or member.project_id != project.id:
        abort(404)
    db.session.delete(member)
    db.session.commit()
    flash("Integrante retirado del proyecto.", "success")
    return redirect(url_for("projects.detail", project_id=project.id))


@projects_bp.route("/<int:project_id>/phases", methods=["POST"])
@login_required
def add_phase(project_id):
    project = visible_project_or_404(project_id)
    if not project_manager(project):
        abort(403)
    form = PhaseForm()
    if form.validate_on_submit():
        phase = Phase(
            project_id=project.id,
            name=form.name.data.strip(),
            description=form.description.data.strip(),
            position=form.position.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
        )
        db.session.add(phase)
        db.session.commit()
        flash("Fase agregada al proyecto.", "success")
    else:
        flash("No se pudo agregar la fase; revisa los datos.", "danger")
    return redirect(url_for("projects.detail", project_id=project.id))


@projects_bp.route("/<int:project_id>/phases/<int:phase_id>/delete", methods=["POST"])
@login_required
def delete_phase(project_id, phase_id):
    project = visible_project_or_404(project_id)
    if not project_manager(project):
        abort(403)
    phase = db.session.get(Phase, phase_id)
    if phase is None or phase.project_id != project.id:
        abort(404)
    db.session.delete(phase)
    db.session.commit()
    flash("Fase eliminada.", "success")
    return redirect(url_for("projects.detail", project_id=project.id))
