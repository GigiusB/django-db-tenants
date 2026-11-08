# Resolvers

A [resolver](../../glossary.md#resolver) maps a request to a client. The middleware calls the one named by `DB_TENANTS["RESOLVER"]`.

## Contract

```python
def resolver(request) -> Client | None: ...
```

| Result | Meaning |
|---|---|
| a `Client` | serve the request from that client's database |
| `None` | no tenant: serve from the shared database |
| raises `TenantNotFound` / `TenantInactive` | refuse: the middleware returns the not-found response |

The resolver runs on every non-exempt request, so it must be cheap: use the cached lookups of the [registry](registry.md).

## Built-in resolvers

| Resolver | Looks at | Status check | Use when |
|---|---|---|---|
| `resolve_by_host` (default) | host name without port; `CONTROL_HOSTS` return `None` | only `active` clients | each tenant has its own domains |
| `resolve_by_header` | the `X-Tenant` header (`HTTP_X_TENANT`), a client slug; no header returns `None` | none | an API gateway sets the tenant |

!!! warning "resolve_by_header trusts the header"
    Anyone who can reach the application directly can pick a tenant by sending `X-Tenant`. Use it only behind a gateway that sets or strips the header. It also serves suspended clients, because slug lookups do not check the status.

## Write your own

Example: tenant from the first path segment, `/t/<slug>/...`:

```python
# myproject/tenancy.py
from django_db_tenants.registry import get_client


def resolve_by_path(request):
    parts = request.path.split("/")
    if len(parts) > 2 and parts[1] == "t":
        client = get_client(parts[2])  # raises TenantNotFound
        if not client.is_active:
            from django_db_tenants.exceptions import TenantInactive

            raise TenantInactive(client.slug)
        return client
    return None
```

```python
DB_TENANTS = {"RESOLVER": "myproject.tenancy.resolve_by_path"}
```

::: django_db_tenants.resolvers
