# Middleware

`TenantMiddleware` resolves the tenant of each request, registers its database and activates it for the request's lifetime. It supports both WSGI and ASGI stacks.

```python
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django_db_tenants.middleware.TenantMiddleware",  # before sessions and auth
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
]
```

## Behaviour

| Request | `request.tenant` | Database for tenant apps | Response |
|---|---|---|---|
| Path starts with an `EXEMPT_PATHS` prefix | `None` | shared | the view's |
| Resolver returns `None` (control host) | `None` | shared | the view's |
| Resolver returns a client | the client | the client's | the view's |
| Resolver raises `TenantError` | not set | | `NOT_FOUND_HANDLER(request, exc)`, or `404 Unknown tenant.` |

The full sequence is described in [Architecture](../../architecture/#request-lifecycle).

## Custom not-found response

```python
# myproject/tenancy.py
from django.shortcuts import render


def tenant_not_found(request, exc):
    return render(request, "unknown_tenant.html", {"host": request.get_host()}, status=404)


# settings.py
DB_TENANTS = {"NOT_FOUND_HANDLER": "myproject.tenancy.tenant_not_found"}
```

`exc` is a `TenantNotFound` or a `TenantInactive`; see [Exceptions](../exceptions/).

::: django_db_tenants.middleware
