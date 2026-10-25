# FRECARGO · Control de operaciones

Primera base funcional para gestionar envíos de FRECARGO desde el navegador.
Desarrollada con Python, Django 5.2 y conexión configurada para MySQL. Interfaz
adaptable a computador y celular, en español, con los colores `#03152d`,
`#026aee` y `#fcfbfb`.

**Estado:** versión inicial para desarrollo y pruebas. No está publicada en
internet ni conectada a un servidor MySQL del negocio. El código aún no se ha
subido a GitHub: la conexión de la cuenta reconocida no mostró instalaciones
ni repositorios accesibles al preparar esta entrega.

## Qué puedes hacer

- Entrar con cuentas individuales y cambiar tu contraseña.
- Registrar y editar clientes; desactivarlos sin borrar sus envíos.
- Registrar envíos con guía interna automática, referencia del cliente,
  recogida, destino, contacto, descripción y tarifa en pesos colombianos.
- Asignar o reasignar un mensajero activo.
- Buscar por guía, referencia, destinatario, cliente o dirección; filtrar por estado.
- Consultar un resumen de todos los registros o de los asignados a tu cuenta.
- Registrar salida a ruta, entrega, novedad, devolución o cancelación.
- Consultar quién modificó cada envío, cuándo y qué datos corrigió.

| Cuenta | Acceso |
| --- | --- |
| Administración (superusuario) | Toda la operación y creación/desactivación de cuentas |
| Coordinación | Clientes, todos los envíos, correcciones y asignaciones |
| Mensajero | Solo sus envíos asignados; cambios de estado permitidos y observaciones |

No hay registro público de cuentas. El administrador crea cada usuario.
La tarifa es un dato del envío: todavía no representa facturación, recaudo
ni liquidación del mensajero.

## Qué instalar

Guía principal para Windows. Usa **Python 3.13 de 64 bits**; la verificación
local de esta entrega se ejecutó con Python 3.12.

| Herramienta | Para qué sirve | Enlace oficial |
| --- | --- | --- |
| Visual Studio Code | Abrir y editar el proyecto | [VS Code](https://code.visualstudio.com/) |
| Extensión Python de Microsoft | Ejecutar y depurar Python en VS Code | [Python en VS Code](https://code.visualstudio.com/docs/languages/python) |
| Python 3.13 | Ejecutar Django | [Descargas para Windows](https://www.python.org/downloads/windows/) |
| MySQL Community Server 8.4 LTS | Guardar los datos de la operación | [MySQL Server](https://dev.mysql.com/downloads/mysql/8.4.html) |
| Git | Versionar el código y sincronizarlo con GitHub | [Instalación de Git](https://git-scm.com/downloads) |

Visual Studio y Visual Studio Code son productos distintos. Esta carpeta
incluye configuración para VS Code, aunque también puedes trabajar desde
otra terminal/editor. MySQL Workbench es una interfaz opcional para administrar
la base: instalar Workbench no instala por sí solo el servidor MySQL.

No hace falta instalar Node.js ni React para esta versión.

## 1. Abrir y preparar el proyecto

Descomprime el ZIP y abre en VS Code la carpeta `frecargo-app`, donde está
`manage.py`. En una terminal PowerShell situada en esa carpeta:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements-mysql.txt
.\.venv\Scripts\python.exe scripts/init_env.py
```

Estos comandos usan directamente el ejecutable del entorno virtual; no
necesitas modificar las políticas de ejecución de PowerShell.
`init_env.py` crea una clave aleatoria para Django y conserva un `.env`
existente sin sobrescribirlo. Selecciona `.venv` como intérprete de Python
en VS Code.

Si instalaste Python 3.12, sustituye `py -3.13` por `py -3.12`.

## 2. Preparar MySQL

Inicia el servicio MySQL. Desde MySQL Command Line Client o tu administrador
de SQL, entra como administrador de MySQL y ejecuta lo siguiente, **sustituyendo
la contraseña de ejemplo por una clave propia y distinta de tus contraseñas de usuario**:

```sql
CREATE DATABASE frecargo CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'frecargo_app'@'localhost' IDENTIFIED BY 'REEMPLAZA_POR_UNA_CLAVE_PROPIA';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, REFERENCES
ON frecargo.* TO 'frecargo_app'@'localhost';
```

Las tablas las crea Django mediante migraciones; no las construyas manualmente.
El usuario anterior tiene permisos de desarrollo y migración sobre esa base.
Antes del despliegue, separa el usuario que ejecuta migraciones del que atiende
la aplicación; el segundo puede limitarse a SELECT, INSERT, UPDATE y DELETE.

Abre `.env` y escribe la misma contraseña en `DB_PASSWORD`. Los valores
principales deben quedar así:

```dotenv
DB_ENGINE=mysql
DB_NAME=frecargo
DB_USER=frecargo_app
DB_PASSWORD='TU_CLAVE_PROPIA'
DB_HOST=127.0.0.1
DB_PORT=3306
```

Conserva la clave `DJANGO_SECRET_KEY` generada por el script. No envíes `.env`
a GitHub ni lo compartas en conversaciones. El archivo ya está excluido
mediante `.gitignore`.

## 3. Crear tablas y tu primera cuenta

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py createsuperuser
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

Elige tu propio usuario y contraseña cuando se soliciten.
Abre [la aplicación local](http://127.0.0.1:8000/) en ese computador.

Desde **Usuarios**, crea las cuentas del equipo. Asigna el rol **Coordinación**
o **Mensajero**. Mantén desmarcados los privilegios de superusuario y acceso
al sitio de administración para los usuarios ordinarios; su rol basta para
usar la aplicación. Solo las personas que deban administrar cuentas necesitan
una cuenta de superusuario.

El flujo inicial es: registrar un cliente, registrar un envío, asignarlo a un
mensajero, iniciar ruta y registrar la entrega o novedad. Para marcar una
entrega se exige el nombre de quien recibió; novedades, devoluciones y
cancelaciones exigen una observación.

## Probar ahora sin esperar a instalar MySQL

Esta alternativa crea una base **SQLite de demostración** independiente de
MySQL. Sirve para explorar el proyecto localmente. No migra datos a MySQL ni
debe utilizarse como base compartida de la operación.

Si ya creaste `.venv`, omite la primera línea:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate --settings=config.settings_demo
.\.venv\Scripts\python.exe manage.py seed_demo --settings=config.settings_demo
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000 --settings=config.settings_demo
```

`seed_demo` genera seis envíos ficticios y las cuentas `admin_demo` y
`mensajero_demo` con contraseñas aleatorias que muestra una sola vez en la
terminal. Conserva esas claves para entrar. Si repites el comando, no reinicia
las contraseñas ni duplica los envíos.

Si olvidaste una contraseña de la demo:

```powershell
.\.venv\Scripts\python.exe manage.py changepassword admin_demo --settings=config.settings_demo
```

La demo solo acepta conexiones desde el propio computador. Los datos demo
no están incluidos en el ZIP: se generan al ejecutar los comandos.

## Usarla desde varios dispositivos

Todos los dispositivos deben entrar a **una misma instancia de la aplicación**,
conectada a **una misma base MySQL**. Cada persona tendrá su cuenta de la
aplicación; no necesita usuario ni contraseña de MySQL en su teléfono.

- En desarrollo, tu computador ejecuta la aplicación y MySQL.
- Para probar en una misma red de confianza, añade la IP local del computador
  a `DJANGO_ALLOWED_HOSTS` y ejecuta `runserver 0.0.0.0:8000` con la configuración
  MySQL normal. En el otro dispositivo entra a `http://IP_LOCAL:8000`.
  Usa datos ficticios en esa prueba HTTP; el computador debe seguir encendido
  y la red/firewall debe permitir ese puerto solo en la red privada.
- Para trabajar desde redes distintas, hay que desplegar la aplicación con
  HTTPS y una base accesible para el servidor. Ese despliegue aún está pendiente.
  No abras el puerto 3306 de MySQL al público ni publiques `runserver` en internet.

Los cambios se consultan al recargar la pantalla. Esta versión todavía no tiene
notificaciones automáticas, actualización en tiempo real ni modo sin conexión.

## GitHub y trabajo con Codex

Nombre propuesto: `frecargo-app`, con visibilidad **privada**. GitHub guarda el
código y su historial de versiones. No aloja por sí solo esta aplicación Django
ni sirve como base de datos.

1. [Crea un repositorio](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-new-repository)
   privado y vacío con ese nombre, sin README ni `.gitignore` adicionales.
2. Habilita el acceso de tu conexión de GitHub a ese repositorio.
3. Comparte el enlace para continuar el trabajo allí.

Si deseas subir esta base tú mismo, ejecuta desde la carpeta del proyecto:

```powershell
git init -b main
git add .
git status
git commit -m "Base inicial de control de operaciones FRECARGO"
git remote add origin URL_HTTPS_DE_TU_REPOSITORIO
git push -u origin main
```

Sustituye el marcador por el enlace real. Revisa `git status` antes del commit:
no deben aparecer `.env`, bases, copias de seguridad ni datos de clientes.
Autentícate con el flujo de GitHub de tu equipo, sin pegar tokens en el código.

La carpeta `.github/workflows` contiene una ejecución de pruebas con MySQL 8.4
para cuando el repositorio tenga GitHub Actions habilitado. Esa ejecución
**no se ha corrido en GitHub todavía**. `AGENTS.md` explica a Codex las reglas
del proyecto para las siguientes modificaciones.

## Verificación y desarrollo

Pruebas rápidas con SQLite, sin servidor MySQL:

```powershell
.\.venv\Scripts\python.exe manage.py test --settings=config.settings_test
```

`settings_test` usa SQLite por defecto, incluso si tu `.env` normal apunta a
MySQL. Solo cambia a MySQL si `DB_ENGINE=mysql` está definida en el entorno de
la terminal; usa otra terminal sin esa variable para ejecutar las pruebas
rápidas. Las pruebas con MySQL crean y
destruyen una base de pruebas separada; requieren una cuenta con esos permisos
y deben ejecutarse en un entorno de desarrollo o en GitHub Actions.

Consulta [VALIDACION.md](docs/VALIDACION.md) para saber qué se verificó realmente
y [ARQUITECTURA.md](docs/ARQUITECTURA.md) para la estructura y el siguiente alcance.

## Si aparece un error al instalar o conectar

- **`py` no se reconoce:** instala Python o reinicia la terminal; usa `python`
  si ese comando identifica la versión correcta en tu equipo.
- **No se instala `mysqlclient`:** usa Python de 64 bits y actualiza pip. En
  Windows el proyecto distribuye ruedas binarias para versiones compatibles;
  compilarlo requiere herramientas adicionales. Sigue las instrucciones del
  [controlador oficial del proyecto](https://github.com/PyMySQL/mysqlclient).
- **En Linux:** instala `python3-dev`, `default-libmysqlclient-dev`,
  `build-essential` y `pkg-config` con el gestor del sistema antes de instalar
  `requirements-mysql.txt`.
- **`Access denied`:** revisa usuario, contraseña y host de `.env`. El usuario
  MySQL es distinto del usuario con que inicias sesión en la aplicación.
- **`Can't connect to MySQL server`:** revisa que MySQL esté iniciado y que el
  puerto corresponda a tu instalación.
- **`DisallowedHost`:** agrega a `DJANGO_ALLOWED_HOSTS` el nombre o IP exacto
  desde el cual entras. No uses `*`.
- **Otra persona actualizó el envío:** recarga, revisa el estado vigente y
  decide tu cambio sobre esa información. La aplicación conserva la actualización anterior.

## Pendiente para usar datos reales en internet

El despliegue debe configurar un servicio permanente, dominio/HTTPS,
`DJANGO_DEBUG=0`, claves propias, hosts/orígenes válidos, conexión protegida a
MySQL, copias de seguridad verificadas y limitación de intentos de inicio de
sesión. No hay aún protección específica contra fuerza bruta en esta versión.
Configura también monitoreo de errores y un procedimiento para restaurar la base.
Antes de abrir el acceso, ejecuta las pruebas con MySQL y revisa las alertas de
`python manage.py check --deploy` con la configuración del servidor.

Waitress está incluido como servidor WSGI compatible con Windows/Linux.
La configuración concreta del alojamiento, proxy HTTPS y servicio persistente
se hará al elegir dónde alojar la aplicación. No se han contratado servicios.

Fuentes técnicas: [instalación de Django](https://docs.djangoproject.com/en/5.2/topics/install/),
[MySQL en Django](https://docs.djangoproject.com/en/5.2/ref/databases/#mysql-notes)
y [descargas de Django](https://www.djangoproject.com/download/).
