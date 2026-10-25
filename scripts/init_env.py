"""Crea configuración local sin sobrescribir claves existentes."""
from pathlib import Path
import secrets

root = Path(__file__).resolve().parent.parent
target = root / ".env"
if target.exists():
    raise SystemExit("Ya existe .env; se conservó sin cambios.")
template = (root / ".env.example").read_text(encoding="utf-8")
with target.open("x", encoding="utf-8") as out:
    out.write(template.replace("GENERAR_CON_scripts_init_env_py", secrets.token_urlsafe(64)))
try:
    target.chmod(0o600)
except OSError:
    pass
print("Se creó .env. Configura DB_PASSWORD antes de ejecutar las migraciones.")
