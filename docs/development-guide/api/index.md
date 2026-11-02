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

Integration points referenced from settings by dotted path are public too: `TenantMiddleware`, `TenantRouter`, the resolvers, `tenant_key_func`, the SSO URLs, `with_tenant` and `for_each_tenant`, the provisioning functions, the database strategies and the exceptions.

## Modules

| Page | Module | Use it to |
|---|---|---|
| [Settings](settings/) | `conf` | Configure the library with `DB_TENANTS` |
| [Context](context/) | `context` | Read or set the active tenant |
| [Middleware](middleware/) | `middleware` | Resolve the tenant of each request |
| [Resolvers](resolvers/) | `resolvers` | Map a request to a client, or write your own mapping |
| [Router](router/) | `router` | Route queries and migrations |
| [Database registration](db/) | `db` | Register or drop a tenant's connection alias |
| [Database strategies](strategies/) | `strategies` | Decide how a tenant database is reached, created and dropped; write your own |
| [Registry](registry/) | `registry` | Look clients up by host or slug, with caching |
| [Provisioning](provisioning/) | `provisioning` | Create and migrate tenant databases |
| [Background tasks](tasks/) | `tasks` | Run tasks and batch jobs per tenant |
| [Cache isolation](cache/) | `cache` | Namespace cache keys per tenant |
| [SSO](sso/) | `sso` | Per-tenant OpenID Connect login |
| [Encryption](encryption/) | `fields`, `crypto` | Encrypt secrets at rest |
| [Admin](admin/) | `admin` | Manage clients in the Django admin |
| [Exceptions](exceptions/) | `exceptions` | Handle resolution errors |

Modules not listed (`apps`, `signals`, `migrations`) have no API of their own; [Architecture](../architecture/) describes what they do.

## Next steps

Start with the [Settings](settings/) reference.
