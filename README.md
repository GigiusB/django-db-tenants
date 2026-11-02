# django-db-tenants

[![CI](https://github.com/GigiusB/django-db-tenants/actions/workflows/ci.yml/badge.svg)](https://github.com/GigiusB/django-db-tenants/actions/workflows/ci.yml)

Database-per-client multi-tenancy for Django.

* One **shared** database holds the client registry. Every client gets its **own database** with its own `auth` users, sessions and application tables.
* Tenant databases are registered in `django.db.connections` **at runtime**, so adding, suspending or re-pointing a client never requires a restart.
* Per-tenant **OpenID Connect SSO** (Entra ID, Okta, Keycloak, Google, …) configured as data on the client row.

## Install

```bash
pip install django-db-tenants          # or: pip install -e path/to/django-db-tenants
```

```python
# settings.py
INSTALLED_APPS = [
    "django_db_tenants",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    ...,
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django_db_tenants.middleware.TenantMiddleware",  # before sessions + auth
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    ...,
]

DATABASE_ROUTERS = ["django_db_tenants.router.TenantRouter"]

DATABASES = {
    # The template: its ENGINE/OPTIONS/CONN_MAX_AGE etc. are copied for each tenant.
    # It also stores the client registry. Its user needs CREATEDB to provision tenants.
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "control",
        "USER": "app",
        "PASSWORD": "...",
        "HOST": "db",
        "CONN_MAX_AGE": 60,
    }
}

ALLOWED_HOSTS = [".yourapp.com"]

DB_TENANTS = {
    "CONTROL_HOSTS": ["admin.yourapp.com"],  # served from the shared DB
    "ENCRYPTION_KEY": env(
        "ENCRYPTION_KEY"
    ),  # Fernet key; python -c "from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())"
}
```

```python
# urls.py
urlpatterns = [path("admin/", admin.site.urls), path("sso/", include("django_db_tenants.sso.urls")), ...]
```

Migrate the shared database once:

```bash
python manage.py migrate
```

## Onboarding a client (no restart)

```bash
python manage.py provision_tenant acme \
    --name "ACME S.p.A." \
    --domain acme.yourapp.com \
    --db-name tenant_acme \
    --oidc-issuer https://login.microsoftonline.com/<tenant-id>/v2.0 \
    --oidc-client-id ... --oidc-client-secret ...
```

This creates the `Client` + `ClientDomain` rows, runs `CREATE DATABASE`, migrates the new database and marks the client `active`. Within `CACHE_TTL` seconds (default 60) every worker will serve `acme.yourapp.com` from `tenant_acme`. The same is available as an admin action on the Client list.

How a client's database is reached is decided by its **database strategy** (`Client.db_strategy`, a [django-strategy-field](https://github.com/saxix/django-strategy-field) `StrategyField`), configured by the encrypted JSON `Client.db_params`. The built-in `TemplateOverlay` lays `db_params` (`HOST`, `USER`, `PASSWORD`, `OPTIONS`, ...; also settable with `--db-host/--db-user/--db-password` or `--db-params '{...}'`) over the template connection; omitted keys fall back to it, so the simplest setup is many databases on one server with one role. Register your own strategies with `DB_TENANTS["DATABASE_STRATEGIES"]`.

## How the routing works

1. `TenantMiddleware` resolves the host to a `Client` (cached), calls `ensure_db_registered(client)`, and sets a `ContextVar` for the duration of the request.
2. `ensure_db_registered` asks the client's database strategy for its connection settings (by default: the template entry from `connections.settings` with the client's `db_params` laid over it) and stores them under the client's slug. Django opens connections lazily from that dict, so the alias is live immediately. Each process does this independently the first time it meets a client; changed credentials are detected through `Client.updated_at` and re-registered.
3. `TenantRouter` sends `SHARED_APPS` (just `django_db_tenants` by default) to the template DB and everything else to the current tenant alias. With no tenant active (control hosts, management commands) it routes to the template DB, which also carries tenant-app tables so superusers can log in to `/admin/` there.

Django does not follow relations across databases, so **never add a ForeignKey from a tenant app to `Client`**; store `client.slug` instead and look it up.

## Deploying migrations

```bash
python manage.py migrate            # shared DB
python manage.py migrate_tenants    # every active tenant DB; exits 1 on any failure
```

## Background jobs

Middleware never runs for Celery/RQ/cron, so pass the tenant explicitly:

```python
from django_db_tenants.tasks import with_tenant, for_each_tenant


@shared_task
@with_tenant
def send_invoices(tenant):  # tenant = slug or Client
    Invoice.objects.filter(sent=False)  # routed to that tenant's DB


for_each_tenant(lambda client: Invoice.objects.count())
```

Or directly:

```python
from django_db_tenants import tenant_context

with tenant_context("acme"):
    ...
```

`manage.py tenant_shell acme` opens a shell with the tenant active.

## SSO

With `sso_enabled` on a client, `/sso/login/` redirects to that client's IdP, `/sso/callback/` validates the ID token (state, nonce and signature are checked by Authlib), finds or creates the user **in the tenant database** via `SSO_USER_SYNC`, and logs them in. `/sso/logout/` performs RP-initiated logout when the IdP advertises `end_session_endpoint`.

Register `https://<client-domain>/sso/callback/` as the redirect URI at each IdP.

Customize user mapping (group → permissions, allowed e-mail domains, etc.):

```python
DB_TENANTS = {"SSO_USER_SYNC": "myapp.sso.sync_user"}


def sync_user(client, userinfo, request):
    ...
    return user  # or None to deny
```

## Cache isolation

Tenants share your cache servers. Without namespacing, two tenants caching the same key
(`cache.set("dashboard-stats", ...)`) read each other's data. Add the tenant key function to
every cache that tenant code uses:

```python
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379",
        "KEY_FUNCTION": "django_db_tenants.cache.tenant_key_func",
    }
}
```

* With a tenant active, keys become `<KEY_PREFIX>:<version>:@<slug>:<key>`.
* With no tenant (control hosts, management commands, `tenant_context(None)`), keys keep Django's
  default format, so existing shared keys don't move. Use `with tenant_context(None):` to read or
  write a deliberately shared key from tenant code.
* The library's own registry keys (`django_db_tenants:*`) are never namespaced, so invalidation works
  from any context.
* This also covers the cache session backend and anything else built on `django.core.cache`.
  `cache.clear()` still clears the whole backend, for every tenant.

## Settings reference

| Key | Default | Purpose |
|---|---|---|
| `TEMPLATE_ALIAS` | `"default"` | Shared DB and connection template |
| `SHARED_APPS` | `("django_db_tenants",)` | Apps living only in the shared DB |
| `DATABASE_STRATEGIES` | `()` | Extra database strategies (dotted paths) clients may use; `TemplateOverlay` is built in |
| `TENANT_APPS_ON_DEFAULT` | `True` | Also create tenant tables in the shared DB |
| `RESOLVER` | `resolve_by_host` | `callable(request) -> Client \| None`; `resolve_by_header` also included |
| `CONTROL_HOSTS` | `()` | Hosts routed to the shared DB |
| `EXEMPT_PATHS` | `("/healthz",)` | Path prefixes that skip resolution |
| `NOT_FOUND_HANDLER` | `None` | `callable(request, exc) -> HttpResponse` |
| `CACHE_ALIAS` / `CACHE_TTL` | `"default"` / `60` | Host lookup cache |
| `ENCRYPTION_KEY` | derived from `SECRET_KEY` | Fernet key for stored secrets |
| `SSO_USER_SYNC` | `default_user_sync` | Claims → user |
| `SSO_AUTH_BACKEND` | `ModelBackend` | Backend recorded on login |
| `SSO_LOGIN_REDIRECT_URL` / `SSO_LOGOUT_REDIRECT_URL` | `"/"` | |
| `SSO_RP_INITIATED_LOGOUT` | `True` | Redirect to IdP on logout |

## Operational notes

* **Connections**: each worker may hold one connection per tenant it has served. Keep `CONN_MAX_AGE` low or put PgBouncer in front for large fleets.
* **Cache**: use a shared cache (Redis/Memcached) in production so all workers see client changes within `CACHE_TTL`, and enable [cache isolation](#cache-isolation). With `LocMemCache` each process has its own TTL window, which still works, just less consistently.
* **Secrets**: `db_params` (which holds the database password) and `oidc_client_secret` are Fernet-encrypted at rest. Set `ENCRYPTION_KEY` explicitly; otherwise rotating `SECRET_KEY` makes them unreadable.
* **Tests**: see [Development](#development) and `tests/_extra/testutils` for fixtures that give each test real, isolated tenant databases.

## Development

Requires [uv](https://docs.astral.sh/uv/).

```bash
uv sync                          # creates .venv with the `dev` dependency group
uv run pre-commit install        # ruff, ty, django-upgrade, uv-lock, … on every commit
uv run pytest                    # test suite (current Python + Django, SQLite)
TEST_DB=pg uv run pytest      # … against PostgreSQL (or TEST_DB=mysql)
uv run tox -p auto               # full Python × Django × database matrix, plus `lint` and `type`
uv run tox -e py313-dj52-pg      # one env: <python>-<django>-<sqlite|pg|mysql>
uv run ty check                  # type checking
uv run ruff check --fix . && uv run ruff format .
uv run mkdocs serve              # developer's guide (docs/) on http://127.0.0.1:8000/
                                 # published from develop: https://gigiusb.github.io/django-db-tenants/
```

### Test databases

SQLite needs nothing. The `pg` and `mysql` envs read their connection from
`TEST_PG_*` / `TEST_MYSQL_*` (`HOST`, `PORT`, `USER`, `PASSWORD`, `NAME`), taken
from the environment or from `.env` at the project root. Start from `.env.example`.
The accounts must be allowed to create and drop databases. Each run creates
`test_<NAME>[_<tox env>]` plus one `test_tenant_*` database per tenant, and drops them
afterwards.

Servers that cover the whole matrix: PostgreSQL 15+ and MySQL 8.4+.
`docker-compose.yml` provides both on ports 55432 / 53306, matching `.env.example`:

```bash
docker compose up -d --wait
cp .env.example .env
uv run tox -p auto
```

MySQL uses `mysqlclient`, which needs the MySQL client headers (`libmysqlclient-dev`
or similar) to build.

Layout:

```
src/django_db_tenants/       the library
tests/                   all tests (pytest + pytest-django)
tests/_extra/testutils/  test utilities, importable as `testutils` (on the pytest pythonpath)
    settings.py          test settings (extend the demo's)
    databases.py         TEST_DB backend selection, .env loading
    factories.py         factory_boy factories: ClientFactory, ClientDomainFactory, UserFactory, NoteFactory
    plugin.py            fixtures: tenant_factory, acme, globex, tenant_db_name, tenant_template_db
    tenants.py           reset_tenant_state(), tenant_login(), template DB cloning per backend
    sso.py               FakeOIDCClient for SSO view tests
tests/demo/              example Django project using the library (see tests/demo/README.md)
```

Writing tests:

```python
from notes.models import Note
from testutils.factories import NoteFactory, UserFactory

from django_db_tenants import tenant_context


def test_notes_are_per_tenant(client, acme, globex):  # acme/globex: migrated tenant DBs
    with tenant_context(acme):
        NoteFactory.create(author=UserFactory.create())
    with tenant_context(globex):
        assert not Note.objects.exists()
    assert client.get("/whoami/", HTTP_HOST="acme.test").json()["tenant"] == "acme"
```

Each tenant gets a database cloned from a template migrated once per session, so tests
stay fast: a file copy on SQLite, `CREATE DATABASE … TEMPLATE` on PostgreSQL, a
table-by-table copy on MySQL. Tenant databases are *not* rolled back by the test
transaction; isolation comes from each test getting fresh databases, which are dropped
when it ends. Use the `tenant_db_name` fixture when a test creates a tenant database
itself (e.g. through `provision()`). Use `freezegun` for anything time-based
(cache TTLs, `updated_at`-driven re-registration).
