# Exceptions

| Exception | Raised when | Raised by |
|---|---|---|
| `TenantError` | Base class; catch it to handle both cases below | |
| `TenantNotFound` | No client matches a host or slug. The message is the host or slug | `get_client_for_host`, `get_client`, `tenant_context`, the resolvers |
| `TenantInactive` | The client exists but its status is not `active`. The message is the slug | `get_client_for_host`, `resolve_by_host` |

`TenantMiddleware` turns any `TenantError` raised by the resolver into the not-found response (`NOT_FOUND_HANDLER`, or a 404). Elsewhere, for example in `tenant_context("unknown")`, the exception propagates.

```python
from django_db_tenants import tenant_context
from django_db_tenants.exceptions import TenantNotFound

try:
    with tenant_context(slug):
        ...
except TenantNotFound:
    log.warning("No tenant %s", slug)
```

::: django_db_tenants.exceptions
