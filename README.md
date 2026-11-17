# DevProject Manager — Hitos 1, 2 y 3

Aplicación web modular con Flask, SQLAlchemy, SQLite y Bootstrap para administrar usuarios y proyectos de software. Los hitos implementados incluyen autenticación y RBAC, proyectos con equipo y fases EDT, tareas vinculadas a fases, tablero Kanban, filtros y registro de horas planificadas frente a reales. Riesgos y reportes ejecutivos quedan para las entregas posteriores.

Repositorio oficial: https://github.com/MibzarMaldonado/DevProject-Manager

## Requisitos previos

- Windows 10/11 con PowerShell 5.1 o superior.
- Python 3.10 o superior y `pip`.
- Git, si se clonará desde un repositorio.
- Navegador moderno.

## Obtener el proyecto

```powershell
cd "d:\ruta\de\trabajo"
git clone https://github.com/MibzarMaldonado/DevProject-Manager.git DevProject-Manager
cd DevProject-Manager
```

Si ya tienes los archivos en la carpeta abierta de VS Code, omite el comando de clonación y continúa desde esa carpeta.

## Entorno virtual y dependencias

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Si PowerShell bloquea la activación:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Para configurar VS Code, selecciona el intérprete `.venv\Scripts\python.exe`.

## Configuración

Copia el ejemplo y genera una clave propia:

```powershell
Copy-Item .env.example .env
$env:SECRET_KEY = [Convert]::ToBase64String([Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
$env:DATABASE_URL = "sqlite:///$((Resolve-Path .).Path.Replace('\','/'))/instance/devproject.db"
```

PowerShell no carga automáticamente `.env`. Antes de arrancar Flask exporta las variables en la misma terminal:

```powershell
$env:SECRET_KEY = "una-clave-larga-generada-localmente"
$env:DATABASE_URL = "sqlite:///$((Resolve-Path .).Path.Replace('\','/'))/instance/devproject.db"
$env:FLASK_APP = "run.py"
```

`.env.example` contiene solamente valores de ejemplo. No incluyas claves reales en el repositorio. Para producción, `COOKIE_SECURE=true` requiere HTTPS y un proxy reverso configurado correctamente.

## Inicializar y crear el primer administrador

El comando crea las tablas y solicita de forma segura los datos del primer administrador:

```powershell
python -m flask --app run.py init-admin
```

Escribe el nombre y correo solicitados. La contraseña no se muestra al introducirla ni se registra en logs. Debe tener al menos 12 caracteres e incluir al menos tres tipos entre minúsculas, mayúsculas, números y símbolos.

El comando falla sin modificar datos si ya existe un administrador. No hay credenciales administrativas predeterminadas.

## Recuperar la contraseña de un administrador

Cuando `init-admin` informa que ya existe un administrador, utiliza el procedimiento de recuperación local. Antes de ejecutarlo, abre PowerShell en la carpeta del proyecto, activa el entorno y configura `SECRET_KEY` y `DATABASE_URL` exactamente con los mismos valores utilizados por la aplicación. Con el valor predeterminado, la ruta efectiva es:

```powershell
D:\DOCUMENTOS 7MO\Gestión de Proyectos de Software\Unidad III\Plataforma web\instance\devproject.db
```

Ejecuta:

```powershell
.\.venv\Scripts\Activate.ps1
python -m flask --app run.py reset-admin-password
```

El comando mostrará los correos de los administradores activos. Confirma el correo exacto y responde `y` a la solicitud final. Las contraseñas nueva y de confirmación se introducirán sin mostrarse en pantalla y deben cumplir la misma política de fortaleza. El comando conserva el usuario, su correo, su rol y su estado; únicamente reemplaza `password_hash` con el hash generado por la aplicación. Cierra el acceso antiguo al restablecerlo. El procedimiento no descifra ni revela contraseñas existentes.

Si no existe un administrador activo seleccionado, el comando termina sin modificar la base. No se crearán cuentas, no se cambiarán roles ni se eliminarán usuarios. Para recuperar una cuenta inactiva, restablecerla en este comando requiere antes decidir si corresponde activar esa cuenta mediante una operación administrativa revisada; esta primera entrega no permite inhabilitar o recuperar cuentas fuera del procedimiento local anterior.

## Ejecutar la aplicación

```powershell
python run.py
```

Abre `http://127.0.0.1:5000/login` y inicia sesión con el administrador creado. Cambia `FLASK_DEBUG=0` o evita el modo debug fuera de desarrollo. La clave secreta y las cookies seguras son obligatorias en producción.

## Ejecutar pruebas

```powershell
python -m pytest -q
```

Las pruebas usan una base SQLite temporal en memoria y crean sus propios datos. No dependen de una cuenta real ni de `instance/devproject.db`.

## Funcionalidades y permisos

- **Administrador:** gestiona usuarios, proyectos, equipo, fases y todas las tareas.
- **Project Manager del proyecto:** administra el proyecto, sus integrantes, fases y tareas.
- **Desarrollador asignado:** consulta su proyecto, actualiza el estado de sus tareas y registra o elimina sus propios registros de tiempo.
- **Cliente / Stakeholder:** consulta los proyectos a los que fue asignado y sus tareas; no puede modificarlos.
- El tablero permite filtrar por responsable y estado. Cada tarea compara las horas estimadas con la suma de registros reales fechados.
- Los formularios validan estados, fechas, presupuesto, fase y responsable dentro del mismo proyecto; las operaciones POST usan protección CSRF.

El primer administrador se crea de forma interactiva con `init-admin`. Después, usa **Administrar usuarios** para crear cuentas de prueba de desarrollador y cliente y **Equipo** para asignarlas al proyecto. No se distribuyen contraseñas compartidas ni cuentas predeterminadas.

## Comprobaciones incluidas

```powershell
python -m pytest -q
```

La suite cubre autenticación y RBAC, restricciones de proyectos y fases, creación/edición/eliminación de tareas, asignaciones, cambios de estado, filtros, registro de horas y acceso de clientes.

## Errores comunes

- **SECRET_KEY no está configurada:** define `SECRET_KEY` antes de iniciar Flask.
- **No se puede activar .venv:** ejecuta `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`.
- **ModuleNotFoundError:** confirma que el entorno virtual está activo y ejecuta `python -m pip install -r requirements.txt`.
- **La sesión no mantiene el usuario:** verifica que se usa la misma base, que el servidor no está reiniciando y que las cookies están habilitadas.
- **Falta la base de datos:** ejecuta primero `python -m flask --app run.py init-admin`.
- **El 403 aparece al crear usuarios:** inicia sesión con un usuario cuyo rol sea `admin`.
- **Directorio instance ignorado:** el archivo de base de datos local no se versiona; este es el comportamiento esperado.

## Git y archivos locales

`.gitignore` excluye `.venv/`, `venv/`, `.env`, `instance/`, bases SQLite locales y artefactos de pruebas.

**Importante:** `.gitignore` no hace que Git deje de rastrear archivos que ya estaban incluidos en el índice. Si un entorno o secreto fuera agregado previamente por otra persona, hay que retirarlo del índice deliberadamente sin borrar los archivos locales:

```powershell
python -m pip freeze
# Ejemplo de retiro: no modifica el archivo local, solo el índice
 git rm --cached .env
 git rm -r --cached .venv instance
```

No ejecutes `git reset --hard` ni `git clean -fd`. Para registrar el avance que ya haya sido probado:

```powershell
git status
git add .
git diff --cached --stat
git commit -m "Implementar autenticación y administración de usuarios"
```

El repositorio oficial ya tiene configurado el remoto `origin`. Revisa los cambios y publícalos desde la rama principal:

```powershell
git status
git diff --check
git log -5 --oneline
git add README.md app tests
git commit -m "Describir el avance implementado"
git push -u origin main
```

No publiques `.env`, claves reales ni bases SQLite locales. El historial y los commits publicados se consultan en el enlace del repositorio oficial.
