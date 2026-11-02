"""App settings.

Override any key in your Django settings:

    DB_TENANTS = {
        "CONTROL_HOSTS": ["admin.example.com"],
        "CACHE_TTL": 30,
    }
"""

from django.conf import settings
from django.utils.module_loading import import_string

DEFAULTS = {
    # Alias whose connection settings are used as a template for every tenant DB.
    # Also the alias that holds the Client registry (shared tables).
    "TEMPLATE_ALIAS": "default",
    # Apps whose tables live ONLY in the template/shared database.
    # Keep this small: anything with a FK to auth.User or contenttypes must be
    # a tenant app, because Django does not follow relations across databases.
    "SHARED_APPS": ("django_db_tenants",),
    # Also create tenant-app tables in the shared DB. Lets superusers log in on a
    # control host that is not mapped to any client.
    "TENANT_APPS_ON_DEFAULT": True,
    # Extra database strategies (dotted paths of DatabaseStrategy subclasses) that
    # clients may use, registered when the app is ready. TemplateOverlay is built in.
    "DATABASE_STRATEGIES": (),
    # Dotted path of a callable(request) -> Client | None. None means "no tenant"
    # (route to TEMPLATE_ALIAS). Raise TenantNotFound for unknown hosts.
    "RESOLVER": "django_db_tenants.resolvers.resolve_by_host",
    # Hosts that are served from the shared DB (admin / control plane).
    "CONTROL_HOSTS": (),
    # URL path prefixes that skip tenant resolution entirely (health checks, etc).
    "EXEMPT_PATHS": ("/healthz",),
    # Dotted path of a callable(request, exc) -> HttpResponse, used when no tenant
    # matches. Defaults to a plain 404.
    "NOT_FOUND_HANDLER": None,
    # Cache used for host -> client lookups.
    "CACHE_ALIAS": "default",
    "CACHE_TTL": 60,
    # Fernet key (urlsafe base64, 32 bytes) for DB passwords / OIDC secrets.
    # If None a key is derived from SECRET_KEY (rotating SECRET_KEY then breaks
    # decryption, so set this explicitly in production).
    "ENCRYPTION_KEY": None,
    # SSO
    "SSO_USER_SYNC": "django_db_tenants.sso.sync.default_user_sync",
    "SSO_AUTH_BACKEND": "django.contrib.auth.backends.ModelBackend",
    "SSO_LOGIN_REDIRECT_URL": "/",
    "SSO_LOGOUT_REDIRECT_URL": "/",
    "SSO_RP_INITIATED_LOGOUT": True,
}

_IMPORT_STRINGS = {"RESOLVER", "NOT_FOUND_HANDLER", "SSO_USER_SYNC"}


class AppSettings:
    def __getattr__(self, name):
        if name not in DEFAULTS:
            raise AttributeError(name)
        user_settings = getattr(settings, "DB_TENANTS", {}) or {}
        value = user_settings.get(name, DEFAULTS[name])
        if name in _IMPORT_STRINGS and isinstance(value, str):
            value = import_string(value)
        return value


app_settings = AppSettings()
