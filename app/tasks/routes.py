from decimal import Decimal

from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models import Phase, Project, ProjectMember, Task, WorkLog
from app.projects.routes import project_manager, visible_project_or_404
from app.tasks import tasks_bp
from app.tasks.forms import TaskForm, TaskStatusForm, WorkLogForm


STATUS_LABELS = {
    "todo": "Por hacer",
    "in_progress": "En progreso",
    "review": "En revisión",
    "done": "Concluida",
}
PRIORITY_LABELS = {"low": "Baja", "medium": "Media", "high": "Alta", "urgent": "Urgente"}


def task_for_project_or_404(project, task_id):
    task = db.session.get(Task, task_id)
    if task is None or task.project_id != project.id:
        abort(404)
    return task


def can_update_task_status(project, task):
    return current_user.role != "client" and (
        project_manager(project)
        or (
        task.assignee_user_id == current_user.id
        and any(member.user_id == current_user.id for member in project.members)
        )
    )


def configure_task_choices(form, project):
    form.phase_id.choices = [(phase.id, phase.name) for phase in project.phases]
    form.assignee_user_id.choices = [
        (member.user_id, f"{member.user.full_name} ({member.user.email})")
        for member in project.members
        if member.project_role in ("developer", "project_manager") and member.user.is_active
    ]


def total_logged_hours(task):
    return sum((log.hours for log in task.work_logs), Decimal("0.00"))


@tasks_bp.route("/<int:project_id>/tasks")
@login_required
def board(project_id):
    project = visible_project_or_404(project_id)
    status_filter = request.args.get("status", "")
    assignee_filter = request.args.get("assignee", "")
    if status_filter and status_filter not in STATUS_LABELS:
        abort(400)
    query = db.select(Task).where(Task.project_id == project.id)
    if status_filter:
        query = query.where(Task.status == status_filter)
    if assignee_filter:
        try:
            assignee_id = int(assignee_filter)
        except ValueError:
            abort(400)
        if assignee_id not in {member.user_id for member in project.members}:
            abort(400)
        query = query.where(Task.assignee_user_id == assignee_id)
    tasks = db.session.scalars(query.order_by(Task.created_at.desc())).all()
    members = [member for member in project.members if member.user.is_active]
    status_form = TaskStatusForm()
    return render_template(
        "tasks/board.html",
        project=project,
        tasks=tasks,
        members=members,
        selected_status=status_filter,
        selected_assignee=assignee_filter,
        status_labels=STATUS_LABELS,
        priority_labels=PRIORITY_LABELS,
        status_form=status_form,
        can_manage=project_manager(project),
        logged_hours={task.id: total_logged_hours(task) for task in tasks},
    )


@tasks_bp.route("/<int:project_id>/tasks/new", methods=["GET", "POST"])
@login_required
def create(project_id):
    project = visible_project_or_404(project_id)
    if not project_manager(project):
        abort(403)
    form = TaskForm()
    configure_task_choices(form, project)
    if not form.phase_id.choices:
        flash("Agrega una fase al proyecto antes de crear tareas.", "warning")
        return redirect(url_for("projects.detail", project_id=project.id))
    if not form.assignee_user_id.choices:
        flash("Asigna al menos un desarrollador al proyecto antes de crear tareas.", "warning")
        return redirect(url_for("projects.detail", project_id=project.id))
    if form.validate_on_submit():
        phase = db.session.get(Phase, form.phase_id.data)
        if phase is None or phase.project_id != project.id:
            abort(400)
        task = Task(
            project_id=project.id,
            phase_id=phase.id,
            title=form.title.data.strip(),
            description=(form.description.data or "").strip(),
            priority=form.priority.data,
            status=form.status.data,
            assignee_user_id=form.assignee_user_id.data,
            planned_hours=form.planned_hours.data,
        )
        task.hourly_rate = form.hourly_rate.data
        db.session.add(task)
        db.session.commit()
        flash("Tarea creada correctamente.", "success")
        return redirect(url_for("tasks.detail", project_id=project.id, task_id=task.id))
    return render_template("tasks/form.html", form=form, project=project, heading="Nueva tarea")


@tasks_bp.route("/<int:project_id>/tasks/<int:task_id>")
@login_required
def detail(project_id, task_id):
    project = visible_project_or_404(project_id)
    task = task_for_project_or_404(project, task_id)
    form = WorkLogForm()
    status_form = TaskStatusForm()
    return render_template(
        "tasks/detail.html",
        project=project,
        task=task,
        form=form,
        status_form=status_form,
        can_manage=project_manager(project),
        can_update=can_update_task_status(project, task),
        logged_hours=total_logged_hours(task),
        status_labels=STATUS_LABELS,
        priority_labels=PRIORITY_LABELS,
    )


@tasks_bp.route("/<int:project_id>/tasks/<int:task_id>/edit", methods=["GET", "POST"])
@login_required
def edit(project_id, task_id):
    project = visible_project_or_404(project_id)
    if not project_manager(project):
        abort(403)
    task = task_for_project_or_404(project, task_id)
    form = TaskForm(obj=task)
    configure_task_choices(form, project)
    if form.validate_on_submit():
        phase = db.session.get(Phase, form.phase_id.data)
        if phase is None or phase.project_id != project.id:
            abort(400)
        form.populate_obj(task)
        task.title = task.title.strip()
        task.description = (task.description or "").strip()
        db.session.commit()
        flash("Tarea actualizada correctamente.", "success")
        return redirect(url_for("tasks.detail", project_id=project.id, task_id=task.id))
    return render_template("tasks/form.html", form=form, project=project, heading="Editar tarea")


@tasks_bp.route("/<int:project_id>/tasks/<int:task_id>/delete", methods=["POST"])
@login_required
def delete(project_id, task_id):
    project = visible_project_or_404(project_id)
    if not project_manager(project):
        abort(403)
    task = task_for_project_or_404(project, task_id)
    db.session.delete(task)
    db.session.commit()
    flash("Tarea eliminada.", "success")
    return redirect(url_for("tasks.board", project_id=project.id))


@tasks_bp.route("/<int:project_id>/tasks/<int:task_id>/status", methods=["POST"])
@login_required
def update_status(project_id, task_id):
    project = visible_project_or_404(project_id)
    task = task_for_project_or_404(project, task_id)
    if not can_update_task_status(project, task):
        abort(403)
    form = TaskStatusForm()
    if not form.validate_on_submit():
        flash("Selecciona un estado válido.", "danger")
        return redirect(url_for("tasks.detail", project_id=project.id, task_id=task.id))
    task.status = form.status.data
    db.session.commit()
    flash("Estado de la tarea actualizado.", "success")
    return redirect(url_for("tasks.detail", project_id=project.id, task_id=task.id))


@tasks_bp.route("/<int:project_id>/tasks/<int:task_id>/logs", methods=["POST"])
@login_required
def add_work_log(project_id, task_id):
    project = visible_project_or_404(project_id)
    task = task_for_project_or_404(project, task_id)
    if not can_update_task_status(project, task):
        abort(403)
    form = WorkLogForm()
    if form.validate_on_submit():
        work_log = WorkLog(
            task_id=task.id,
            user_id=current_user.id,
            hours=form.hours.data,
            work_date=form.work_date.data,
            notes=(form.notes.data or "").strip(),
        )
        db.session.add(work_log)
        db.session.commit()
        flash("Horas registradas correctamente.", "success")
    else:
        flash("No se pudo registrar el tiempo; revisa las horas y la fecha.", "danger")
    return redirect(url_for("tasks.detail", project_id=project.id, task_id=task.id))


@tasks_bp.route("/<int:project_id>/tasks/<int:task_id>/logs/<int:log_id>/delete", methods=["POST"])
@login_required
def delete_work_log(project_id, task_id, log_id):
    project = visible_project_or_404(project_id)
    task = task_for_project_or_404(project, task_id)
    work_log = db.session.get(WorkLog, log_id)
    if work_log is None or work_log.task_id != task.id:
        abort(404)
    if work_log.user_id != current_user.id and not project_manager(project):
        abort(403)
    db.session.delete(work_log)
    db.session.commit()
    flash("Registro de horas eliminado.", "success")
    return redirect(url_for("tasks.detail", project_id=project.id, task_id=task.id))
