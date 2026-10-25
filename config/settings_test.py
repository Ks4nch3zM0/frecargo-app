import os

os.environ.setdefault("DB_ENGINE", "sqlite")
os.environ["DJANGO_DEBUG"] = "1"
os.environ["DJANGO_SECRET_KEY"] = "tests-only-" + "x" * 60
from .settings import *  # noqa: F403,E402

DEMO_MODE = False
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
