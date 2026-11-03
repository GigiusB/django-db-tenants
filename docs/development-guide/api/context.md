# Context

`django_db_tenants.context` holds the [tenant context](../../glossary.md#tenant-context): the client whose database the router uses for tenant apps. It is a `ContextVar`, so it is correct under threads, `asyncio` and asgiref's `sync_to_async` / `async_to_sync`.

## Read the active tenant

```python
from django_db_tenants import get_current_tenant, get_current_tenant_alias

client = get_current_tenant()  # Client, or None on the shared database
alias = get_current_tenant_alias()  # "acme", or None
```

In a view, `request.tenant` holds the same client. `get_current_tenant()` also works where there is no request: models, signals, services.

## Run code as a tenant

```python
from django_db_tenants import tenant_context

with tenant_context("acme") as client:  # a slug or a Client
    Order.objects.count()  # acme's database

with tenant_context(None):  # explicitly the shared database
    ...
```

`tenant_context()` looks a slug up through the [registry](registry.md) (raising `TenantNotFound` for unknown slugs, without checking the status), registers the database alias, activates the client and restores the previous value on exit. Contexts nest.

`set_current_tenant()` / `reset_current_tenant()` are the low-level pair the middleware uses; prefer `tenant_context()`, which also registers the alias.

::: django_db_tenants.context
