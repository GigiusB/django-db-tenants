# Client

`django_db_tenants.models.Client`: one [tenant](../../../glossary/#tenant). Table `django_db_tenants_client`, in the [shared database](../../../glossary/#shared-database) only.

A client row tells the library three things: whether the tenant may be served (`status`), how to reach its database (`db_strategy`, `db_name`, `db_params`), and which host names it answers on (its [domains](../client-domain/)). Changing any of them takes effect without a restart.

## Relations

| Relation | Target | Notes |
|---|---|---|
| reverse `domains` | [ClientDomain](../client-domain/) | `client.domains.all()`; deleting a client deletes its domains (`CASCADE`) |
| tenant database | `connections[client.slug]` | not a database relation: the alias is registered at runtime from the [database strategy](../../api/strategies/) |

Tenant-app models must not have a `ForeignKey` to `Client`: it lives in another database. Store the slug instead.

## Fields

### Identity and status

| Field | Type | Required | Default | Meaning |
|---|---|---|---|---|
| `name` | `CharField(200)` | yes | | Display name |
| `slug` | `SlugField(63)`, unique | yes | | The tenant's database alias and cache namespace. Read-only in the admin after creation. `default` and the value of `TEMPLATE_ALIAS` are rejected |
| `status` | `CharField(20)`, choices `Status` | yes | `provisioning` | Only `active` clients are resolved by host |

`Client.Status`:

| Value | Label | Meaning |
|---|---|---|
| `provisioning` | Provisioning | Created, database not ready yet. `provision()` moves it to `active` |
| `active` | Active | Served |
| `suspended` | Suspended | Kept, not served by host: requests get `TenantInactive` (a 404 by default) |

### Database

How the database is reached, created and dropped is up to the client's [database strategy](../../../glossary/#database-strategy); see [Database strategies](../../api/strategies/).

| Field | Type | Required | Default | Meaning |
|---|---|---|---|---|
| `db_strategy` | `StrategyField` (django-strategy-field), stores a dotted path | yes | `django_db_tenants.strategies.TemplateOverlay` | The strategy class; must be registered. Reading it returns an instance bound to the client |
| `db_name` | `CharField(200)` | yes | | Database name (a file path on SQLite) |
| `db_params` | `EncryptedJSONField` | no | `{}` | Strategy parameters, a JSON object, Fernet-encrypted at rest. Keys are defined and validated by the strategy |

With the default `TemplateOverlay` strategy, `db_params` keys are `DATABASES` keys laid over the [template alias](../../../glossary/#template-alias) connection: `ENGINE`, `HOST`, `PORT`, `USER`, `PASSWORD`, `OPTIONS` (merged), `CONN_MAX_AGE`, `CONN_HEALTH_CHECKS`, plus `MAINTENANCE_DB` for PostgreSQL provisioning. Missing keys inherit the template's value. For example:

```json
{"HOST": "db2.internal", "USER": "acme", "PASSWORD": "s3cret", "OPTIONS": {"sslmode": "require"}}
```

Other strategies define other keys: the optional [`OidcStrategy`](../../api/oidc/) adds an `SSO` object with the tenant's OpenID Connect provider.

### Timestamps

| Field | Type | Meaning |
|---|---|---|
| `created_at` | `DateTimeField(auto_now_add=True)` | Creation time |
| `updated_at` | `DateTimeField(auto_now=True)` | Last save; source of `config_version()` |

## Properties and methods

| Member | Returns | Meaning |
|---|---|---|
| `alias` | `str` | The database alias: the slug |
| `is_active` | `bool` | `status == "active"` |
| `get_db_strategy()` | `DatabaseStrategy` | `db_strategy`, or `ImproperlyConfigured` when the stored class cannot be imported |
| `config_version()` | `str` | `updated_at` in ISO format; a new value makes each process re-register the connection (and `OidcStrategy`'s OIDC client) |
| `clean()` | | Rejects reserved slugs and `db_params` the strategy refuses (`validate()`) |

Default ordering: `name`. `str(client)` is `"<name> (<slug>)"`.

## Side effects of saving and deleting

| Action | Effect |
|---|---|
| save | the registry cache entries of the client and its domains are deleted (`signals.py`) |
| delete | same, then the alias is unregistered in the current process. The tenant database itself is **not** dropped |

`clean()` runs only through `full_clean()` (model forms, the admin, `provision_tenant`), not on a plain `save()`.

## Example

```python
from django_db_tenants.models import Client, ClientDomain
from django_db_tenants.provisioning import provision

client = Client(
    name="ACME S.p.A.",
    slug="acme",
    db_name="tenant_acme",
    db_params={"HOST": "db2.internal", "PASSWORD": "s3cret"},  # default strategy: TemplateOverlay
)
client.full_clean()
client.save(using="default")
ClientDomain.objects.using("default").create(client=client, domain="acme.example.com", is_primary=True)
provision(client)  # CREATE DATABASE, migrate, status = active
```

## Next steps

Read [ClientDomain](../client-domain/), or the [`provision_tenant`](../../cli/provision-tenant/) command, which does all of the above in one call.
