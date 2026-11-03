# API reference

Who is this for: developers who call the library from their code, or change it.

Each page explains one module: what it is for, how to use it, then the reference generated from the source (signatures and docstrings).

## Public entry points

Import these from the package root; they are the stable surface:

```python
from django_db_tenants import (
    ensure_db_registered,  # register a client's database alias in this process
    get_current_tenant,  # the active Client, or None
    get_current_tenant_alias,  # the active alias, or None
    tenant_context,  # run a block as a tenant
)
```

Integration points referenced from settings by dotted path are public too: `TenantMiddleware`, `TenantRouter`, the resolvers, `tenant_key_func`, `with_tenant` and `for_each_tenant`, the provisioning functions, the database strategies and the exceptions.

## Modules

| Page | Module | Use it to |
|---|---|---|
| [Settings](settings.md) | `conf` | Configure the library with `DB_TENANTS` |
| [Context](context.md) | `context` | Read or set the active tenant |
| [Middleware](middleware.md) | `middleware` | Resolve the tenant of each request |
| [Resolvers](resolvers.md) | `resolvers` | Map a request to a client, or write your own mapping |
| [Router](router.md) | `router` | Route queries and migrations |
| [Database registration](db.md) | `db` | Register or drop a tenant's connection alias |
| [Database strategies](strategies.md) | `strategies` | Decide how a tenant database is reached, created and dropped; write your own |
| [Registry](registry.md) | `registry` | Look clients up by host or slug, with caching |
| [Provisioning](provisioning.md) | `provisioning` | Create and migrate tenant databases |
| [Background tasks](tasks.md) | `tasks` | Run tasks and batch jobs per tenant |
| [Cache isolation](cache.md) | `cache` | Namespace cache keys per tenant |
| [OIDC strategy](oidc.md) | `oidc` | Optional: per-tenant OpenID Connect single sign-on with `OidcStrategy` |
| [Encryption](encryption.md) | `fields`, `crypto` | Encrypt secrets at rest |
| [Admin](admin.md) | `admin` | Manage clients in the Django admin |
| [Exceptions](exceptions.md) | `exceptions` | Handle resolution errors |

Modules not listed (`apps`, `signals`, `migrations`) have no API of their own; [Architecture](../architecture.md) describes what they do.

## Next steps

Start with the [Settings](settings.md) reference.
