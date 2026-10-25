"""Demostración local separada de la conexión MySQL."""
import os

os.environ["DB_ENGINE"] = "sqlite"
os.environ["DJANGO_DEBUG"] = "1"
os.environ["FRECARGO_DEMO"] = "1"
os.environ["DJANGO_ALLOWED_HOSTS"] = "localhost,127.0.0.1,[::1]"
os.environ["DJANGO_SECRET_KEY"] = "demo-local-no-usar-en-produccion-" + "x" * 50
from .settings import *  # noqa: F403,E402
