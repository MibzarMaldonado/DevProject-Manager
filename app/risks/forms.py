from urllib.parse import urlparse

from flask_wtf import FlaskForm
from wtforms import IntegerField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, NumberRange, URL, ValidationError


class RiskForm(FlaskForm):
    title = StringField("Riesgo", validators=[DataRequired(), Length(max=180)])
    description = TextAreaField("Descripción", default="")
    category = SelectField(
        "Clasificación",
        choices=[
            ("technical", "Técnico"),
            ("financial", "Financiero"),
            ("personnel", "Personal"),
            ("schedule", "Cronograma"),
            ("other", "Otro"),
        ],
        validators=[DataRequired()],
    )
    probability = IntegerField(
        "Probabilidad (1–5)", validators=[DataRequired(), NumberRange(min=1, max=5)]
    )
    impact = IntegerField("Impacto (1–5)", validators=[DataRequired(), NumberRange(min=1, max=5)])
    mitigation = TextAreaField("Mitigación / contingencia", validators=[DataRequired()])
    submit = SubmitField("Guardar riesgo")


class ProjectDocumentForm(FlaskForm):
    title = StringField("Nombre del documento", validators=[DataRequired(), Length(max=160)])
    document_type = SelectField(
        "Tipo",
        choices=[
            ("architecture", "Arquitectura"),
            ("minutes", "Acta / minuta"),
            ("other", "Otro"),
        ],
        validators=[DataRequired()],
    )
    url = StringField("Enlace", validators=[DataRequired(), URL(), Length(max=2048)])
    description = StringField("Descripción", validators=[Length(max=500)], default="")
    submit = SubmitField("Adjuntar enlace")

    def validate_url(self, field):
        parsed = urlparse(field.data or "")
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValidationError("El enlace debe comenzar con http:// o https://.")
