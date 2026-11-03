"""Django settings for the test suite: the demo project plus test-only tweaks."""

from demo.settings import *
from testutils.databases import default_database

ALLOWED_HOSTS = ["*"]

# SQLite (the demo's settings) unless TEST_DB selects PostgreSQL or MySQL.
DATABASES = {"default": default_database(DATABASES["default"])}

# Fast hashing; tests never need real password strength.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "tests",
        "KEY_FUNCTION": "django_db_tenants.cache.tenant_key_func",
    }
}

DB_TENANTS = {
    **DB_TENANTS,
    "CONTROL_HOSTS": ["control.test"],
    "ENCRYPTION_KEY": "MZYwaxOSOeZTj-cTJPpsl3HGW-TyjrKciRexyxY2mHc=",
    "CACHE_TTL": 60,
    "DATABASE_STRATEGIES": ["testutils.strategies.EnvironmentPassword", "django_db_tenants.oidc.OidcStrategy"],
}

# The demo's URLs plus the optional OIDC login views.
ROOT_URLCONF = "testutils.urls"

LOGGING = {"version": 1, "disable_existing_loggers": False}
