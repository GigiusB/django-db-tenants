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
    # Alias that holds the Client registry (shared tables). A copy of its connection
    # settings is passed to every database strategy; the built-in TemplateOverlay
    # derives tenant connections from it.
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
    # Fernet key (urlsafe base64, 32 bytes) for Client.db_params (DB passwords, ...).
    # If None a key is derived from SECRET_KEY (rotating SECRET_KEY then breaks
    # decryption, so set this explicitly in production).
    "ENCRYPTION_KEY": None,
}


class AppSettings:
    """The keys of ``DB_TENANTS``, falling back to ``defaults``.

    Values of ``import_strings`` keys given as dotted paths are imported.
    """

    def __init__(self, defaults: dict, import_strings: frozenset[str] = frozenset()) -> None:
        self._defaults = defaults
        self._import_strings = import_strings

    def __getattr__(self, name):
        if name.startswith("_") or name not in self._defaults:
            raise AttributeError(name)
        user_settings = getattr(settings, "DB_TENANTS", {}) or {}
        value = user_settings.get(name, self._defaults[name])
        if name in self._import_strings and isinstance(value, str):
            value = import_string(value)
        return value


app_settings = AppSettings(DEFAULTS, frozenset({"RESOLVER", "NOT_FOUND_HANDLER"}))
