from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Length

from app.validation import login_email_validator, normalize_email


class LoginForm(FlaskForm):
    email = StringField(
        "Correo electrónico",
        filters=[normalize_email],
        validators=[DataRequired(), login_email_validator, Length(max=255)],
    )
    password = PasswordField("Contraseña", validators=[DataRequired()])
    submit = SubmitField("Iniciar sesión")
