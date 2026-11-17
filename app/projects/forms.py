from flask_wtf import FlaskForm
from wtforms import (
    DateField,
    DecimalField,
    IntegerField,
    SelectField,
    SelectMultipleField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Length, NumberRange, Optional


class ProjectForm(FlaskForm):
    name = StringField("Nombre", validators=[DataRequired(), Length(max=160)])
    description = TextAreaField("Descripción", default="")
    objectives = TextAreaField("Objetivos", default="")
    start_date = DateField("Fecha de inicio", validators=[DataRequired()])
    end_date = DateField("Fecha fin estimada", validators=[DataRequired()])
    base_budget = DecimalField(
        "Presupuesto base", places=2, validators=[DataRequired(), NumberRange(min=0)]
    )
    status = SelectField(
        "Estado",
        choices=[
            ("planning", "En planificación"),
            ("active", "Activo"),
            ("paused", "Pausado"),
            ("finished", "Finalizado"),
        ],
        validators=[DataRequired()],
    )
    submit = SubmitField("Guardar proyecto")

    def validate(self, extra_validators=None):
        if not super().validate(extra_validators):
            return False
        if self.end_date.data < self.start_date.data:
            self.end_date.errors.append("La fecha final debe ser igual o posterior al inicio.")
            return False
        return True


class MemberForm(FlaskForm):
    user_id = SelectField("Integrante", coerce=int, validators=[DataRequired()])
    project_role = SelectField(
        "Rol en el proyecto",
        choices=[
            ("project_manager", "Project Manager"),
            ("developer", "Desarrollador"),
            ("client", "Cliente / Stakeholder"),
        ],
        validators=[DataRequired()],
    )
    submit = SubmitField("Asignar integrante")


class PhaseForm(FlaskForm):
    name = StringField("Fase o hito", validators=[DataRequired(), Length(max=120)])
    description = TextAreaField("Descripción", default="")
    position = IntegerField("Orden", validators=[DataRequired(), NumberRange(min=1)])
    start_date = DateField("Inicio", validators=[Optional()])
    end_date = DateField("Fin", validators=[Optional()])
    submit = SubmitField("Agregar fase")

    def validate(self, extra_validators=None):
        if not super().validate(extra_validators):
            return False
        if self.start_date.data and self.end_date.data and self.end_date.data < self.start_date.data:
            self.end_date.errors.append("La fecha final debe ser igual o posterior al inicio.")
            return False
        return True
