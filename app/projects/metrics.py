from decimal import Decimal

from app.extensions import db
from app.models import Risk, Task


def project_metrics(project):
    tasks = db.session.scalars(
        db.select(Task).where(Task.project_id == project.id).order_by(Task.created_at)
    ).all()
    planned_hours = sum((task.planned_hours for task in tasks), Decimal("0.00"))
    actual_hours = sum(
        (log.hours for task in tasks for log in task.work_logs), Decimal("0.00")
    )
    actual_cost = sum(
        (log.hours * task.hourly_rate for task in tasks for log in task.work_logs),
        Decimal("0.00"),
    )
    completed_tasks = sum(task.status == "done" for task in tasks)
    progress = round(completed_tasks * 100 / len(tasks)) if tasks else 0
    status_counts = {
        status: sum(task.status == status for task in tasks)
        for status in ("todo", "in_progress", "review", "done")
    }
    risk_count = db.session.scalar(
        db.select(db.func.count()).select_from(Risk).where(Risk.project_id == project.id)
    )
    return {
        "tasks": tasks,
        "task_count": len(tasks),
        "completed_tasks": completed_tasks,
        "progress": progress,
        "status_counts": status_counts,
        "planned_hours": planned_hours,
        "actual_hours": actual_hours,
        "actual_cost": actual_cost,
        "budget_balance": project.base_budget - actual_cost,
        "risk_count": risk_count or 0,
    }
