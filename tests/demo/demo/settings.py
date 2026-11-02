"""Settings for the django-db-tenants demo project.

Everything that matters for multi-tenancy is marked with ``# django-db-tenants``.
The demo uses SQLite files under ``tests/demo/var/`` so it runs with no extra
services; point ``DATABASES["default"]`` at PostgreSQL for a realistic setup.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
VAR_DIR = Path(os.environ.get("DEMO_VAR_DIR", BASE_DIR / "var"))
VAR_DIR.mkdir(parents=True, exist_ok=True)

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "demo-insecure-secret-key-do-not-use-in-production")
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"

# Browsers resolve *.localhost to 127.0.0.1, so http://acme.localhost:8000/ works
# without touching /etc/hosts.
ALLOWED_HOSTS = [".localhost", "127.0.0.1"]

INSTALLED_APPS = [
    "django_db_tenants",  # django-db-tenants: shared app (client registry)
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "notes",  # an ordinary app: its tables live in every tenant database
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django_db_tenants.middleware.TenantMiddleware",  # django-db-tenants: before sessions + auth
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "demo.urls"
WSGI_APPLICATION = "demo.wsgi.application"
ASGI_APPLICATION = "demo.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "demo" / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# django-db-tenants: "default" is both the shared database (client registry) and the
# template every tenant connection is copied from.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": VAR_DIR / "control.sqlite3",
    }
}
DATABASE_ROUTERS = ["django_db_tenants.router.TenantRouter"]  # django-db-tenants

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        # django-db-tenants: give each tenant its own cache key namespace.
        "KEY_FUNCTION": "django_db_tenants.cache.tenant_key_func",
    }
}

DB_TENANTS = {  # django-db-tenants
    # Served from the shared database: log in here as a superuser to manage clients.
    "CONTROL_HOSTS": ["localhost", "127.0.0.1"],
    # python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    "ENCRYPTION_KEY": os.environ.get("ENCRYPTION_KEY", "AMQ0qhP2y1GpOwCM0u0xmsp_YBuQr2qCA5VOiP-YbJ4="),
    "CACHE_TTL": 10,
}

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "home"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "loggers": {"django_db_tenants": {"handlers": ["console"], "level": "INFO"}},
}
