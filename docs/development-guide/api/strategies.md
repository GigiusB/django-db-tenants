# Database strategies

A [database strategy](../../../glossary/#database-strategy) decides how a tenant's database is reached, created and dropped. Each `Client` names its strategy in `db_strategy`; the strategy reads its parameters from the client's encrypted `db_params` and its `db_name`.

`db_strategy` is a `StrategyField` from [django-strategy-field](https://github.com/saxix/django-strategy-field): the column stores the dotted path of a class, and reading the attribute returns an **instance bound to the client**:

```python
client.db_strategy  # <TemplateOverlay object>, built as TemplateOverlay(client)
client.db_strategy.client is client  # True
client.get_db_strategy()  # same, but raises ImproperlyConfigured if the class cannot be imported
```

## Who calls the strategy

| Caller | Strategy method |
|---|---|
| `Client.clean()` (admin, `full_clean()`, `provision_tenant`) | `validate()` |
| `ensure_db_registered()` (middleware, `tenant_context()`, `migrate_tenant()`) | `connection_settings(template)` |
| `provisioning.create_database()` / `provision()` | `create_database(if_not_exists)` |
| `provisioning.drop_database()` | `drop_database()` |

`ensure_db_registered()` always resets `TEST["NAME"]` to `None` on what the strategy returns, so no strategy can make a test run reuse the template's test database.

## Shipped strategies

| Strategy | Registered | What it does |
|---|---|---|
| `django_db_tenants.strategies.TemplateOverlay` | always, the default | `DATABASES` keys from `db_params` laid over the template connection; `NAME = client.db_name` |
| `django_db_tenants.oidc.OidcStrategy` | through `DATABASE_STRATEGIES` | `TemplateOverlay`, plus the client's OpenID Connect provider for per-tenant single sign-on. See [OIDC strategy](../oidc/) |

## `TemplateOverlay`

The default for every client: the [template alias](../../../glossary/#template-alias) connection with the client's parameters laid over it. Its `db_params` are shaped like a Django `DATABASES` entry without `NAME`, which comes from `client.db_name`.

| `db_params` key | Effect |
|---|---|
| `ENGINE`, `HOST`, `PORT`, `USER`, `PASSWORD` | Replace the template's value |
| `OPTIONS` (object) | Merged into the template's `OPTIONS` |
| `CONN_MAX_AGE`, `CONN_HEALTH_CHECKS` | Replace the template's value |
| `MAINTENANCE_DB` | PostgreSQL only: the database to connect to for `CREATE` / `DROP DATABASE`. Default `postgres` |

Missing keys, empty strings and `null` inherit the template's value. `NAME` is always `client.db_name`. Any other key fails validation:

```text
{'db_params': ['Template connection + overrides does not accept NAME. Allowed keys: CONN_HEALTH_CHECKS, ..., PORT, USER.']}
```

Examples of `db_params`:

```json
{}
{"HOST": "db2.internal", "USER": "acme", "PASSWORD": "s3cret", "OPTIONS": {"sslmode": "require"}}
{"ENGINE": "django.db.backends.mysql", "HOST": "mysql.internal", "PORT": "3306"}
```

Creating and dropping databases uses the **resulting** connection: its server and its account, which needs the right to create and drop databases.

| Vendor | `create_database()` | `drop_database()` |
|---|---|---|
| PostgreSQL | Connects to `MAINTENANCE_DB` in autocommit, checks `pg_database`, `CREATE DATABASE`. Returns `False` when it already exists (`RuntimeError` with `if_not_exists=False`) | `DROP DATABASE IF EXISTS` |
| MySQL | Connects without a default database, `CREATE DATABASE [IF NOT EXISTS] ... CHARACTER SET utf8mb4` | `DROP DATABASE IF EXISTS` |
| SQLite | Nothing: the file appears on first connection | Deletes the file |
| Others | `NotImplementedError` | `NotImplementedError` |

## Write your own strategy

Subclass `DatabaseStrategy` (or `TemplateOverlay` to keep its behaviour), declare the `db_params` keys it accepts, and register it.

Example: take the password from an environment variable named in `db_params`, so the secret is not stored in the database:

```python
# myproject/tenancy.py
import os

from django.core.exceptions import ImproperlyConfigured
from django_db_tenants.strategies import TemplateOverlay


class EnvironmentPassword(TemplateOverlay):
    label = "Template + password from environment"
    param_keys = TemplateOverlay.settings_keys - {"PASSWORD"} | {"PASSWORD_ENV", "MAINTENANCE_DB"}

    def connection_settings(self, template):
        settings = super().connection_settings(template)
        variable = self.params.get("PASSWORD_ENV")
        if variable:
            try:
                settings["PASSWORD"] = os.environ[variable]
            except KeyError:
                raise ImproperlyConfigured(f"{variable} is not set") from None
        return settings
```

```python
# settings.py
DB_TENANTS = {"DATABASE_STRATEGIES": ["myproject.tenancy.EnvironmentPassword"]}
```

```bash
python manage.py provision_tenant acme --name ACME --db-name acme \
    --db-strategy myproject.tenancy.EnvironmentPassword --db-params '{"PASSWORD_ENV": "ACME_DB_PASSWORD"}'
```

The test suite ships this exact strategy (`tests/_extra/testutils/strategies.py`).

### The contract

| Member | Required | Contract |
|---|---|---|
| `label` | recommended | Name in the admin select and in error messages |
| `param_keys` | recommended | `frozenset` of accepted `db_params` keys; `None` accepts anything |
| `validate()` | no | Raise `ValidationError({"db_params": ...})` for bad parameters; call `super().validate()` |
| `connection_settings(template)` | yes | Return the complete `DATABASES` entry. `template` is a private deep copy of the template alias's settings with Django's defaults filled in: modify it or build a new dict. Called on every (re-)registration, so keep it fast; it may run in any thread |
| `create_database(if_not_exists=True)` | for provisioning | Create the database; return `True` when created |
| `drop_database()` | for dropping | Drop the database if it exists |

Inside a strategy, `self.client` is the `Client` and `self.params` its `db_params` (a dict).

### Registration

The `Client.db_strategy` field accepts only registered classes, both in the admin select and in `full_clean()`.

| Way | When |
|---|---|
| `DB_TENANTS["DATABASE_STRATEGIES"] = ["dotted.Path"]` | Registered when the app is ready. Use this in projects |
| `strategies.registry.register(MyStrategy)` | From code, for example in your own `AppConfig.ready()` |

Registering a strategy never creates a migration: the field's choices are not part of the schema.

### When a strategy class disappears

A client row whose strategy class cannot be imported still loads (lists, admin), with `db_strategy` set to `None`. Using it raises `ImproperlyConfigured` naming the missing class, and `full_clean()` reports the field as invalid. Keep removed strategies importable until no client uses them.

## Changing a client's strategy or parameters

Saving the client changes its [config version](../../../glossary/#config-version), so every process re-registers the connection with the new settings the next time it meets the client.

::: django_db_tenants.strategies
