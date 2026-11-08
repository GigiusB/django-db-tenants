# Registry

`django_db_tenants.registry` looks clients up in the shared database, through the cache named by `CACHE_ALIAS`, for `CACHE_TTL` seconds.

| Function | Returns | Raises |
|---|---|---|
| `get_client_for_host(host)` | the client that owns the domain (host lower-cased, without port) | `TenantNotFound` for unknown hosts (cached too), `TenantInactive` for non-active clients |
| `get_client(slug)` | the client with that slug, any status | `TenantNotFound` |
| `invalidate(client)` | | deletes the slug key and every host key of the client |
| `invalidate_host(host)` | | deletes one host key |

```python
from django_db_tenants.registry import get_client

client = get_client("acme")
if not client.is_active:
    ...
```

The signal handlers call `invalidate()` and `invalidate_host()` when `Client` and `ClientDomain` rows change. Call them yourself after changing rows with `QuerySet.update()` or outside Django. Cache keys and limits are described in [Architecture](../architecture.md#client-lookup-cache-and-invalidation).

::: django_db_tenants.registry
