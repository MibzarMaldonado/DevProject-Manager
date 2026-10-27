import getpass

import click
from app.extensions import db
from app.models import User
from app.validation import EMAIL_PATTERN, normalize_email, validate_password_strength


def register_cli(app):
    @app.cli.command("init-admin")
    def init_admin():
        """Inicializa la base de datos y crea de forma segura el primer administrador."""
        db.create_all()
        if db.session.scalar(db.select(User).where(User.role == "admin")):
            raise click.ClickException("Ya existe un administrador; no se modificó ningún usuario.")

        full_name = click.prompt("Nombre completo")
        email = normalize_email(click.prompt("Correo electrónico"))
        if not full_name.strip():
            raise click.ClickException("El nombre completo es obligatorio.")
        if not EMAIL_PATTERN.fullmatch(email):
            raise click.ClickException("El correo electrónico no tiene un formato válido.")
        if db.session.scalar(db.select(User).where(db.func.lower(User.email) == email)):
            raise click.ClickException("Ya existe un usuario con ese correo.")

        password = getpass.getpass("Contraseña (no visible): ")
        password_error = validate_password_strength(password)
        if password_error:
            raise click.ClickException(password_error)
        if password != getpass.getpass("Confirmar contraseña: "):
            raise click.ClickException("Las contraseñas no coinciden.")

        user = User(full_name=full_name.strip(), email=email, role="admin", is_active=True)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.secho("Administrador creado correctamente.", fg="green")

    @app.cli.command("reset-admin-password")
    def reset_admin_password():
        """Restablece de forma segura la contraseña de un administrador local."""
        admins = db.session.scalars(
            db.select(User).where(User.role == "admin", User.is_active).order_by(User.email)
        ).all()
        if not admins:
            raise click.ClickException("No existe un administrador activo disponible.")

        click.echo("Administradores activos encontrados:")
        for admin in admins:
            click.echo(f"- {admin.email}")

        email = normalize_email(click.prompt("Confirma el correo exacto del administrador"))
        selected = next((admin for admin in admins if admin.email == email), None)
        if selected is None:
            raise click.ClickException("El correo no corresponde a un administrador activo.")

        if not click.confirm(
            f"¿Restablecer la contraseña de {selected.email}? Esta acción reemplaza el acceso anterior",
            default=False,
        ):
            raise click.ClickException("Operación cancelada; no se modificó ningún usuario.")

        password = getpass.getpass("Nueva contraseña (no visible): ")
        password_error = validate_password_strength(password)
        if password_error:
            raise click.ClickException(password_error)
        if password != getpass.getpass("Confirmar nueva contraseña: "):
            raise click.ClickException("Las contraseñas no coinciden.")

        selected.set_password(password)
        db.session.commit()
        click.secho("Contraseña de administrador restablecida correctamente.", fg="green")
