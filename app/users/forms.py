from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, Length

from app.validation import password_validator


class CreateUserForm(FlaskForm):
    full_name = StringField(
        "Nombre completo", validators=[DataRequired("Ingresa el nombre completo."), Length(min=2, max=120)]
    )
    email = StringField(
        "Correo electrónico", validators=[DataRequired(), Email(message="Ingresa un correo válido."), Length(max=255)]
    )
    password = PasswordField(
        "Contraseña", validators=[DataRequired("Ingresa una contraseña."), password_validator]
    )
    role = SelectField(
        "Rol", choices=[("developer", "Desarrollador"), ("client", "Cliente"), ("admin", "Administrador")]
    )
    is_active = BooleanField("Usuario activo", default=True)
    submit = SubmitField("Registrar usuario")
