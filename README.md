# DevProject Manager — primera entrega

Aplicación web modular con Flask para autenticación y administración segura de usuarios. Esta entrega no incluye todavía proyectos, fases, tareas, riesgos ni reportes.

## Requisitos previos

- Windows 10/11 con PowerShell 5.1 o superior.
- Python 3.10 o superior y `pip`.
- Git, si se clonará desde un repositorio.
- Navegador moderno.

## Obtener el proyecto

```powershell
cd "d:\ruta\de\trabajo"
git clone <URL_DEL_REPOSITORIO> DevProject-Manager
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

## Comprobaciones incluidas

- Página de login y acceso privado.
- Login correcto e incorrecto.
- Bloqueo de usuarios inactivos.
- Invalidación de sesión al cerrar sesión.
- Acceso y creación de usuarios por administradores.
- Correos duplicados y contraseñas débiles.
- Restricción por rol y protección CSRF.
- Almacenamiento mediante hash de contraseña.

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

No se crea un commit ni se hace push automáticamente. Antes de un push, conserva el remoto configurado y revisa `git remote -v`.

## Preparar y publicar en GitHub

Después de revisar el resultado localmente, inicia Git si la carpeta todavía no es un repositorio:

```powershell
git init
git add .
git status
git diff --cached --stat
```

Después de comprobar que `.env`, `.venv`, `instance/` y las bases SQLite no aparecen en `git status`, crea el primer commit:

```powershell
git add README.md REQUERIMIENTOS.txt requirements.txt .gitignore .env.example app tests run.py
git commit -m "Implementar autenticación y administración de usuarios"
```

En GitHub crea un repositorio público vacío sin inicializarlo con README. Luego conecta el remoto y publica solo cuando hayas decidido la rama y revisado el contenido:

```powershell
git branch -M main
git remote add origin https://github.com/<USUARIO>/<REPOSITORIO>.git
git push -u origin main
```

Este proyecto no incluye automáticamente el repositorio remoto ni realiza el push. Antes de subirlo, usa `git log --stat --oneline -1` y `git remote -v`; nunca publiques `.env`, claves reales ni archivos `.db` locales.
