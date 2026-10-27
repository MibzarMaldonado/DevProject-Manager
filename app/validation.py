import re

from wtforms.validators import ValidationError

EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def normalize_email(value):
    return value.strip().lower() if value else ""


def validate_password_strength(password):
    if len(password) < 12:
        return "La contraseña debe tener al menos 12 caracteres."
    if password.lower() in {"password", "contrasena", "contraseña"}:
        return "La contraseña es demasiado común."
    checks = (any(c.islower() for c in password), any(c.isupper() for c in password),
              any(c.isdigit() for c in password), any(not c.isalnum() for c in password))
    if sum(checks) < 3:
        return "Incluye al menos tres tipos: minúsculas, mayúsculas, números o símbolos."
    return None


def login_email_validator(form, field):
    if not EMAIL_PATTERN.fullmatch(field.data or ""):
        raise ValidationError("Ingresa un correo válido.")


def password_validator(form, field):
    message = validate_password_strength(field.data or "")
    if message:
        raise ValidationError(message)
