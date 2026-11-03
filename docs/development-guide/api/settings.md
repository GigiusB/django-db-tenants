# Settings

The library reads one Django setting, the `DB_TENANTS` dictionary. Every key is optional; missing keys take the defaults below (`conf.py`).

```python
# settings.py
DB_TENANTS = {
    "CONTROL_HOSTS": ["admin.example.com"],
    "ENCRYPTION_KEY": os.environ["ENCRYPTION_KEY"],
    "CACHE_TTL": 30,
}
```

## Reference

| Key | Type | Default | Effect |
|---|---|---|---|
| `TEMPLATE_ALIAS` | `str` | `"default"` | `DATABASES` alias of the [shared database](../../../glossary/#shared-database), which holds the client registry. A copy of its settings is passed to every [database strategy](../strategies/); the built-in `TemplateOverlay` derives tenant connections from it. Clients cannot use it as slug |
| `SHARED_APPS` | iterable of app labels | `("django_db_tenants",)` | Apps whose tables live only in the shared database. Keep it small: an app with a foreign key to `auth.User` or `contenttypes` must stay a tenant app |
| `TENANT_APPS_ON_DEFAULT` | `bool` | `True` | Also create tenant-app tables in the shared database, so superusers can log in on a [control host](../../../glossary/#control-host) |
| `DATABASE_STRATEGIES` | iterable of dotted paths | `()` | Extra [database strategies](../strategies/) clients may use, registered when the app is ready. The built-in `TemplateOverlay` is always registered |
| `RESOLVER` | dotted path or callable | `"django_db_tenants.resolvers.resolve_by_host"` | `callable(request) -> Client | None`. `None` means no tenant (shared database); raise `TenantNotFound` or `TenantInactive` to refuse the request. See [Resolvers](../resolvers/) |
| `CONTROL_HOSTS` | iterable of host names | `()` | Hosts that `resolve_by_host` serves from the shared database. Compared without port, case-insensitively |
| `EXEMPT_PATHS` | iterable of path prefixes | `("/healthz",)` | Requests whose path starts with one of these skip resolution; `request.tenant` is `None` |
| `NOT_FOUND_HANDLER` | dotted path, callable or `None` | `None` | `callable(request, exc) -> HttpResponse` for requests whose resolver raised `TenantError`. `None` returns `404 Unknown tenant.` |
| `CACHE_ALIAS` | `str` | `"default"` | `CACHES` alias for host and slug lookups (and for `OidcStrategy`'s discovery metadata) |
| `CACHE_TTL` | `int`, seconds | `60` | Lifetime of the cached lookups; the longest a per-process cache can serve a stale client |
| `ENCRYPTION_KEY` | `str` or `bytes`, or `None` | `None` | Fernet key for `db_params`. `None` derives a key from `SECRET_KEY`. See [Encryption](../encryption/) |
`RESOLVER` and `NOT_FOUND_HANDLER` accept a dotted path, imported on each access, or the callable itself.

The optional [`OidcStrategy`](../oidc/#settings) reads its settings from the `OIDC` sub-dict of `DB_TENANTS`.

## Other settings the library depends on

| Setting | Requirement |
|---|---|
| `INSTALLED_APPS` | contains `"django_db_tenants"` |
| `MIDDLEWARE` | `"django_db_tenants.middleware.TenantMiddleware"` before `SessionMiddleware` and `AuthenticationMiddleware` |
| `DATABASE_ROUTERS` | `["django_db_tenants.router.TenantRouter"]` |
| `DATABASES[TEMPLATE_ALIAS]` | the shared database, and the template the built-in strategy derives tenant connections from; the resulting account needs the right to create databases for [provisioning](../provisioning/) |
| `ALLOWED_HOSTS` | every tenant domain, for example `[".example.com"]` |
| `CACHES` | a shared backend (Redis, Memcached) in production; `KEY_FUNCTION = "django_db_tenants.cache.tenant_key_func"` on caches tenant code uses |
| `SECRET_KEY` | source of the encryption key when `ENCRYPTION_KEY` is unset |

## Reading settings in code

```python
from django_db_tenants.conf import app_settings

app_settings.CACHE_TTL  # value from DB_TENANTS, or the default
app_settings.RESOLVER  # already imported: a callable
app_settings.UNKNOWN_KEY  # AttributeError
```

`app_settings` reads `settings.DB_TENANTS` on every access, so `override_settings` in tests takes effect immediately. The Fernet instance is the exception: it is cached, see [Encryption](../encryption/).

::: django_db_tenants.conf
