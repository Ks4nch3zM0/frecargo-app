# Trabajo en FRECARGO

- Aplicación Django 5.2; base operativa MySQL 8.4/InnoDB.
- Interfaz y mensajes en español. Colores: #03152d, #026aee, #fcfbfb.
- La lógica de cambios de envíos vive en `operations/services.py`.
- Mantener autorización en servidor; los mensajeros solo acceden a sus envíos.
- Guardar cada mutación del envío y su historial en una sola transacción.
- Preservar el control de versión en los formularios que modifican envíos.
- No habilitar edición directa de envíos/historial en Django Admin.
- Generar migraciones cuando cambien modelos. No modificar tablas a mano.
- Nunca subir `.env`, claves, SQLite, respaldos o datos de clientes al repositorio.
- Demo y pruebas deben usar datos ficticios. La demo no es una conexión MySQL.
- Verificar con `python manage.py test --settings=config.settings_test`.
- Para cambios en transacciones o esquema, ejecutar también las pruebas de
  MySQL del flujo de GitHub Actions; no afirmar esa validación si no se ejecutó.
- Mantener actualizados README y el alcance real de cada entrega.
