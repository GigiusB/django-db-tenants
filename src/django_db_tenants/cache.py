"""Per-tenant cache key namespacing.

Tenants share cache servers, so two tenants caching ``"dashboard-stats"`` would
read each other's data. Plug :func:`tenant_key_func` into each cache that
tenant code uses::

    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": "redis://127.0.0.1:6379",
            "KEY_FUNCTION": "django_db_tenants.cache.tenant_key_func",
        }
    }

Keys written while a tenant is active get the tenant's alias in them; keys
written with no tenant (control hosts, management commands, ``tenant_context(None)``)
keep Django's default format, so turning this on does not move existing shared
keys. The library's own registry keys (``django_db_tenants:...``) are always shared,
whichever tenant is active.

``cache.clear()`` still clears the whole backend, for every tenant.
"""

from .context import get_current_tenant_alias

#: Keys starting with this are never namespaced (the host/slug -> Client registry).
SHARED_KEY_PREFIX = "django_db_tenants:"


def tenant_key_func(key: str, key_prefix: str, version: int | str) -> str:
    """Django ``KEY_FUNCTION`` that namespaces keys by the current tenant.

    No tenant:     ``<KEY_PREFIX>:<version>:<key>``           (Django's default)
    Tenant active: ``<KEY_PREFIX>:<version>:@<alias>:<key>``

    Tenant aliases are slugs, which cannot contain ``@``, so tenant namespaces
    never overlap each other.
    """
    alias = get_current_tenant_alias()
    if alias is None or key.startswith(SHARED_KEY_PREFIX):
        return f"{key_prefix}:{version}:{key}"
    return f"{key_prefix}:{version}:@{alias}:{key}"
