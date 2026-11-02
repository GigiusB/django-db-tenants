# Cache isolation

Tenants share the cache servers. Without namespacing, two tenants caching the same key (`cache.set("dashboard-stats", ...)`) read each other's data. `tenant_key_func` prevents that.

```python
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379",
        "KEY_FUNCTION": "django_db_tenants.cache.tenant_key_func",
    }
}
```

Set it on every cache that tenant code uses.

## Key format

| Situation | Key |
|---|---|
| No tenant active (control hosts, management commands, `tenant_context(None)`) | `<KEY_PREFIX>:<version>:<key>`, Django's default, so existing shared keys do not move |
| Tenant active | `<KEY_PREFIX>:<version>:@<slug>:<key>` |
| Key starts with `django_db_tenants:` (the registry's own keys) | Django's default format, whatever tenant is active |

Slugs cannot contain `@`, so tenant namespaces never overlap each other or the shared one.

## Notes

- To read or write a deliberately shared key from tenant code, wrap the call in `with tenant_context(None):`.
- The cache session backend and anything else built on `django.core.cache` are namespaced too.
- `cache.clear()` still clears the whole backend, for every tenant.

::: django_db_tenants.cache
