from flask_wtf import FlaskForm
from wtforms import DateField, DecimalField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, NumberRange


class TaskForm(FlaskForm):
    phase_id = SelectField("Fase", coerce=int, validators=[DataRequired()])
    title = StringField("Título", validators=[DataRequired(), Length(max=180)])
    description = TextAreaField("Descripción", default="")
    priority = SelectField(
        "Prioridad",
        choices=[
            ("low", "Baja"),
            ("medium", "Media"),
            ("high", "Alta"),
            ("urgent", "Urgente"),
        ],
        validators=[DataRequired()],
    )
    assignee_user_id = SelectField("Responsable", coerce=int, validators=[DataRequired()])
    planned_hours = DecimalField(
        "Horas planificadas", places=2, validators=[DataRequired(), NumberRange(min=0)]
    )
    hourly_rate = DecimalField(
        "Costo por hora", places=2, validators=[DataRequired(), NumberRange(min=0)], default=0
    )
    status = SelectField(
        "Estado",
        choices=[
            ("todo", "Por hacer"),
            ("in_progress", "En progreso"),
            ("review", "En revisión"),
            ("done", "Concluida"),
        ],
        validators=[DataRequired()],
    )
    submit = SubmitField("Guardar tarea")


class TaskStatusForm(FlaskForm):
    status = SelectField(
        "Estado",
        choices=[
            ("todo", "Por hacer"),
            ("in_progress", "En progreso"),
            ("review", "En revisión"),
            ("done", "Concluida"),
        ],
        validators=[DataRequired()],
    )
    submit = SubmitField("Actualizar estado")


class WorkLogForm(FlaskForm):
    hours = DecimalField(
        "Horas reales", places=2, validators=[DataRequired(), NumberRange(min=0.01)]
    )
    work_date = DateField("Fecha", validators=[DataRequired()])
    notes = StringField("Nota", validators=[Length(max=500)], default="")
    submit = SubmitField("Registrar horas")
