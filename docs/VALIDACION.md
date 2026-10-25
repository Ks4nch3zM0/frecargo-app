# Validación de la entrega inicial

Entrega preparada el 17 de septiembre de 2026.

## Ejecutado

- Python 3.12.14 y Django 5.2.17 en Linux.
- Instalación de las dependencias generales de `requirements.txt`.
- Generación y aplicación de migraciones con SQLite.
- `manage.py check --settings=config.settings_demo`: sin problemas detectados.
- `manage.py makemigrations --check --dry-run --settings=config.settings_test`:
  no se detectaron cambios de modelos sin migración.
- `manage.py test --settings=config.settings_test`: **28 pruebas descubiertas,
  27 aprobadas y 1 omitida** porque SQLite no dispone del bloqueo de filas
  que necesita la prueba de concurrencia.
- Creación local de la demo con seis envíos ficticios y cuentas con claves
  aleatorias; arranque del servidor de desarrollo.

Las pruebas cubren permisos por cuenta, ocultación de envíos ajenos,
restricciones de coordinación, protección CSRF, escape de HTML introducido
como datos, cuentas inactivas, creación mediante formulario, búsqueda y filtros,
entregas con receptor, novedades con motivo, transiciones válidas,
formularios desactualizados, correcciones con historial, transacciones con
reversión ante errores y restricción de la demo a su configuración local.

## Pendiente

- **MySQL real:** este entorno no tenía servidor MySQL ni sus bibliotecas
  nativas. El controlador de MySQL no quedó instalado aquí. La configuración
  y migraciones están preparadas; no se afirma que se haya probado la conexión.
- **Concurrencia real:** el flujo de GitHub Actions incluye MySQL 8.4 y la
  prueba de dos actualizaciones simultáneas, pendiente de su primera ejecución.
- **Revisión visual:** no se completó la descarga del navegador de pruebas.
  Se verificó el HTML servido en las pruebas Django, pero no la presentación
  visual en navegadores reales de computador o celular.
- **Windows:** se incluyen comandos para PowerShell y Python 3.13; esa
  combinación no se ejecutó en esta sesión.
- **GitHub:** la cuenta `Ks4nch3zM0` fue reconocida, pero los listados devolvieron
  cero instalaciones/cuentas instaladas y cero repositorios accesibles. No
  se creó ni modificó ningún repositorio, commit o pull request remoto.
- **Uso por internet:** aplicación sin desplegar; faltan alojamiento, HTTPS,
  configuración de producción, respaldo/restauración y limitación de intentos
  de inicio de sesión.

El ZIP excluye bases de datos, contraseñas generadas, archivos `.env`, entornos
virtuales y dependencias instaladas. Incluye `.env.example` como plantilla.
