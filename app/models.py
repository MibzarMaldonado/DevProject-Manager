from datetime import datetime, timezone
from decimal import Decimal

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db, login_manager


class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="developer")
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        db.CheckConstraint("role IN ('admin', 'developer', 'client')", name="valid_role"),
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        return self.role == "admin"


class Project(db.Model):
    __tablename__ = "projects"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text, nullable=False, default="")
    objectives = db.Column(db.Text, nullable=False, default="")
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    base_budget = db.Column(db.Numeric(12, 2), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="planning")
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        db.CheckConstraint("base_budget >= 0", name="nonnegative_project_budget"),
        db.CheckConstraint(
            "status IN ('planning', 'active', 'paused', 'finished')", name="valid_project_status"
        ),
        db.CheckConstraint("end_date >= start_date", name="valid_project_dates"),
    )

    members = db.relationship(
        "ProjectMember", back_populates="project", cascade="all, delete-orphan"
    )
    phases = db.relationship(
        "Phase", back_populates="project", cascade="all, delete-orphan",
        order_by="Phase.position, Phase.id",
    )


class ProjectMember(db.Model):
    __tablename__ = "project_members"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(
        db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    project_role = db.Column(db.String(24), nullable=False)

    __table_args__ = (
        db.UniqueConstraint("project_id", "user_id", name="unique_project_member"),
        db.CheckConstraint(
            "project_role IN ('project_manager', 'developer', 'client')",
            name="valid_project_member_role",
        ),
    )

    project = db.relationship("Project", back_populates="members")
    user = db.relationship("User")


class Phase(db.Model):
    __tablename__ = "phases"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(
        db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False, default="")
    position = db.Column(db.Integer, nullable=False, default=1)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)

    __table_args__ = (
        db.CheckConstraint("position > 0", name="positive_phase_position"),
        db.CheckConstraint(
            "end_date IS NULL OR start_date IS NULL OR end_date >= start_date",
            name="valid_phase_dates",
        ),
    )

    project = db.relationship("Project", back_populates="phases")
    tasks = db.relationship("Task", back_populates="phase", cascade="all, delete-orphan")


class Task(db.Model):
    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(
        db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    phase_id = db.Column(
        db.Integer, db.ForeignKey("phases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    assignee_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    title = db.Column(db.String(180), nullable=False)
    description = db.Column(db.Text, nullable=False, default="")
    priority = db.Column(db.String(12), nullable=False, default="medium")
    status = db.Column(db.String(16), nullable=False, default="todo")
    planned_hours = db.Column(db.Numeric(8, 2), nullable=False, default=0)
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        db.CheckConstraint(
            "priority IN ('low', 'medium', 'high', 'urgent')", name="valid_task_priority"
        ),
        db.CheckConstraint(
            "status IN ('todo', 'in_progress', 'review', 'done')", name="valid_task_status"
        ),
        db.CheckConstraint("planned_hours >= 0", name="nonnegative_planned_hours"),
    )

    project = db.relationship("Project")
    phase = db.relationship("Phase", back_populates="tasks")
    assignee = db.relationship("User")
    work_logs = db.relationship(
        "WorkLog", back_populates="task", cascade="all, delete-orphan",
        order_by="WorkLog.work_date, WorkLog.id",
    )
    budget_rate = db.relationship(
        "TaskBudgetRate",
        back_populates="task",
        uselist=False,
        cascade="all, delete-orphan",
    )

    @property
    def hourly_rate(self):
        return self.budget_rate.hourly_rate if self.budget_rate else Decimal("0.00")

    @hourly_rate.setter
    def hourly_rate(self, value):
        if self.budget_rate is None:
            self.budget_rate = TaskBudgetRate(hourly_rate=value)
        else:
            self.budget_rate.hourly_rate = value


class WorkLog(db.Model):
    __tablename__ = "work_logs"

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(
        db.Integer, db.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    hours = db.Column(db.Numeric(7, 2), nullable=False)
    work_date = db.Column(db.Date, nullable=False)
    notes = db.Column(db.String(500), nullable=False, default="")
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (db.CheckConstraint("hours > 0", name="positive_logged_hours"),)

    task = db.relationship("Task", back_populates="work_logs")
    user = db.relationship("User")


class TaskBudgetRate(db.Model):
    __tablename__ = "task_budget_rates"

    task_id = db.Column(
        db.Integer, db.ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True
    )
    hourly_rate = db.Column(db.Numeric(10, 2), nullable=False, default=0)

    __table_args__ = (
        db.CheckConstraint("hourly_rate >= 0", name="nonnegative_task_hourly_rate"),
    )

    task = db.relationship("Task", back_populates="budget_rate")


class Risk(db.Model):
    __tablename__ = "risks"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(
        db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title = db.Column(db.String(180), nullable=False)
    description = db.Column(db.Text, nullable=False, default="")
    category = db.Column(db.String(20), nullable=False)
    probability = db.Column(db.Integer, nullable=False)
    impact = db.Column(db.Integer, nullable=False)
    mitigation = db.Column(db.Text, nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        db.CheckConstraint(
            "category IN ('technical', 'financial', 'personnel', 'schedule', 'other')",
            name="valid_risk_category",
        ),
        db.CheckConstraint("probability BETWEEN 1 AND 5", name="valid_risk_probability"),
        db.CheckConstraint("impact BETWEEN 1 AND 5", name="valid_risk_impact"),
    )

    project = db.relationship("Project")

    @property
    def severity(self):
        return self.probability * self.impact

    @property
    def severity_label(self):
        if self.severity >= 17:
            return "Crítico"
        if self.severity >= 10:
            return "Alto"
        if self.severity >= 5:
            return "Medio"
        return "Bajo"


class ProjectDocument(db.Model):
    __tablename__ = "project_documents"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(
        db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    added_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(160), nullable=False)
    document_type = db.Column(db.String(20), nullable=False)
    url = db.Column(db.String(2048), nullable=False)
    description = db.Column(db.String(500), nullable=False, default="")
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        db.CheckConstraint(
            "document_type IN ('architecture', 'minutes', 'other')",
            name="valid_project_document_type",
        ),
    )

    project = db.relationship("Project")
    added_by = db.relationship("User")


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))
