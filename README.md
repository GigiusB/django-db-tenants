# django-db-tenants

[![CI](https://github.com/GigiusB/django-db-tenants/actions/workflows/ci.yml/badge.svg)](https://github.com/GigiusB/django-db-tenants/actions/workflows/ci.yml)

Database-per-client multi-tenancy for Django.

* One **shared** database holds the client registry. Every client gets its **own database** with its own `auth` users, sessions and application tables.
* Tenant databases are registered in `django.db.connections` **at runtime**, so adding, suspending or re-pointing a client never requires a restart.
* How a client's database is reached is decided by its **database strategy**, configured by encrypted per-client parameters. The built-in one derives tenant connections from the shared database's settings; write your own for anything else.

**Documentation:** the developer's guide is at <https://gigiusb.github.io/django-db-tenants/> (sources in [`docs/`](docs/)).

## Install

```bash
pip install django-db-tenants
pip install "django-db-tenants[postgres]"  # extras: postgres, mysql
```

Requires Python 3.11+ and Django 4.2, 5.2, 6.0 or 6.1.

## Configure

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
    ...,
]

DATABASE_ROUTERS = ["django_db_tenants.router.TenantRouter"]

DATABASES = {
    # The shared database (client registry), also the starting point of tenant connections.
    # Its account needs the right to create databases to provision tenants.
    "default": {"ENGINE": "django.db.backends.postgresql", "NAME": "control", "USER": "app", ...},
}

DB_TENANTS = {
    "CONTROL_HOSTS": ["admin.yourapp.com"],  # served from the shared database
    "ENCRYPTION_KEY": env("ENCRYPTION_KEY"),  # Fernet key for the stored client secrets
}
```

```bash
python manage.py migrate  # the shared database
```

## Use

Add a client: this creates its database, migrates it and serves `acme.yourapp.com` from it, without a restart.

```bash
python manage.py provision_tenant acme --name "ACME S.p.A." --domain acme.yourapp.com --db-name tenant_acme
```

Requests are routed to the tenant of their host. Outside a request, activate a tenant yourself:

```python
from django_db_tenants import tenant_context
from django_db_tenants.tasks import with_tenant

with tenant_context("acme"):
    Invoice.objects.count()  # runs on tenant_acme


@with_tenant
def send_invoices(tenant): ...  # background jobs: pass the slug or the Client
```

```bash
python manage.py migrate_tenants  # migrate every active tenant database
```

Users are ordinary Django users in each tenant database, so any Django authentication works.

Next: the [architecture](https://gigiusb.github.io/django-db-tenants/development-guide/architecture/), [database strategies](https://gigiusb.github.io/django-db-tenants/development-guide/api/strategies/), [settings](https://gigiusb.github.io/django-db-tenants/development-guide/api/settings/) and [cache isolation](https://gigiusb.github.io/django-db-tenants/development-guide/api/cache/). The demo project in [`tests/demo`](tests/demo/README.md) shows a complete setup.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) to set up the development environment and run the tests.

## License

django-db-tenants is source-available under the [PolyForm Noncommercial License 1.0.0](LICENSE.md):

- **Noncommercial use is free**: personal study, research, hobby projects, and use by charities, educational institutions, public research organizations and government institutions.
- **Commercial use needs a commercial license**, including a company using the library in its products, services or internal systems. Write to Giovanni Bronzini at <g.bronzini@gmail.com>.

Versions up to 0.2.0 were released under the MIT license.
