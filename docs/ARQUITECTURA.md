# Estructura y próximos pasos

## Decisión inicial

Una aplicación web Django con páginas renderizadas en el servidor. Se evita
necesitar dos proyectos de interfaz/backend para comenzar. Todos los usuarios
trabajan sobre la misma base MySQL a través de la aplicación.

| Pieza | Responsabilidad |
| --- | --- |
| Navegador en PC o celular | Formularios y consulta de datos según la cuenta |
| Django | Sesiones, permisos, validación y reglas de envíos |
| MySQL / InnoDB | Datos compartidos, integridad y transacciones |
| GitHub | Código, revisiones y ejecución de pruebas |

## Carpetas

| Ruta | Contenido |
| --- | --- |
| `accounts/` | Usuario con roles de coordinación y mensajero |
| `operations/models.py` | Clientes, envíos y movimientos |
| `operations/services.py` | Creación, edición, asignación y cambios de estado |
| `operations/views.py` | Pantallas y filtrado por permisos |
| `operations/tests.py` | Acceso, reglas, historial y concurrencia |
| `config/` | Configuración MySQL, demo local, pruebas y rutas |
| `templates/`, `static/` | Interfaz adaptable, sin dependencias web externas |
| `.github/workflows/` | Pruebas automatizadas con MySQL |

Los clientes se relacionan con muchos envíos. Un envío tiene como máximo un
mensajero actual y muchos movimientos. Cada movimiento registra al usuario
que lo realizó. Los datos operativos se conservan; no hay borrado de envíos
ni edición del historial desde la interfaz o el administrador Django.
Un administrador con acceso directo a SQL sí puede alterar los datos: el
historial no es un registro criptográficamente inmutable.

## Estados

| Estado actual | Siguiente acción permitida |
| --- | --- |
| Recibido | Asignar mensajero; cancelar con motivo desde coordinación |
| Asignado | Iniciar ruta; registrar novedad; coordinación puede cancelar |
| En ruta | Entregar con nombre del receptor; novedad; devolución con motivo |
| Novedad | Reintentar ruta; devolver; coordinación puede cancelar |
| Entregado / Devuelto / Cancelado | Consulta; registro cerrado |

Reasignar un envío abierto conserva el estado, salvo que pase de Recibido a
Asignado. El mensajero anterior pierde acceso al envío inmediatamente.
Las fechas se almacenan con zona horaria y se muestran en hora de Bogotá.

## Trabajo simultáneo

Las mutaciones del envío y su movimiento se guardan en una sola transacción.
MySQL bloquea la fila con `select_for_update` mientras se modifica. Cada
formulario envía la versión que vio: si otro usuario ya guardó un cambio, el
formulario antiguo se rechaza. Se debe recargar y revisar antes de reenviar.
El control de versión cubre envíos; el directorio de clientes utiliza edición
convencional y aún no tiene historial ni control de conflicto entre editores.

SQLite se incluye para una demostración de un solo computador. No prueba las
garantías de bloqueo de MySQL. La prueba de concurrencia real se ejecuta solo
en motores con bloqueo de filas y está incluida en el flujo de GitHub Actions.

## Siguiente alcance propuesto

1. Instalar y probar MySQL, habilitar el repositorio y ajustar campos con
   ejemplos reales del trabajo de FRECARGO, sin incorporar información privada al código.
2. Desplegar una instancia con HTTPS, copias de seguridad y cuentas del equipo.
3. Incorporar pruebas de entrega: fotos/firma, almacenamiento privado y controles
   de acceso, una vez definido el proceso de entrega.
4. Importación masiva de pedidos con detección de duplicados y revisión de errores.
5. Gestión de recaudos, costos y liquidaciones, cuando se definan las reglas.
6. Rutas de múltiples paradas: geocodificación, zonas, ventanas de entrega,
   proveedor cartográfico y optimización. No se incluye todavía en esta versión.

No hay integración con Temu, SHEIN, Xcargo ni otros operadores. Una integración
necesita acceso autorizado a sus interfaces o un formato acordado de archivos;
añadir sus nombres a la aplicación no crea esa conexión.
