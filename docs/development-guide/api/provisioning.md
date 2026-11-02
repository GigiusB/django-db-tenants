# Provisioning

`django_db_tenants.provisioning` creates, migrates and drops tenant databases at runtime. [`provision_tenant`](../../cli/provision-tenant/), [`migrate_tenants`](../../cli/migrate-tenants/) and the admin action are built on it. The database work is delegated to the client's [database strategy](../strategies/).

| Function | Effect |
|---|---|
| `create_database(client, if_not_exists=True)` | `client.get_db_strategy().create_database(...)`. Returns `True` when the database was created. With the built-in strategy, an existing PostgreSQL database returns `False`, or raises `RuntimeError` with `if_not_exists=False`; MySQL raises the server's error with `if_not_exists=False` |
| `migrate_tenant(client, **options)` | Registers the alias and runs `migrate --database=<slug>` non-interactively; `options` go to `migrate` (`fake`, `verbosity`, ...) |
| `provision(client, create_db=True, migrate=True, activate=True)` | Create, migrate, then status `active`. Safe to re-run |
| `drop_database(client)` | Closes the current thread's connection to the tenant and unregisters its alias, then `client.get_db_strategy().drop_database()`. The client row is not changed: delete it or set its status yourself |

How each backend is handled by the built-in `TemplateOverlay` strategy is described in [Database strategies](../strategies/#the-built-in-strategy-templateoverlay). The connecting account needs the right to create and drop databases (`CREATEDB` on PostgreSQL, `CREATE` and `DROP` on MySQL).

!!! warning "Dropping a database in use"
    `drop_database()` closes only the calling thread's connection. Other processes or threads still connected to the tenant make PostgreSQL refuse the `DROP`. Suspend the client first, and wait for connections to close (`CONN_MAX_AGE`).

## Example: provisioning in a background job

```python
from django_db_tenants.models import Client
from django_db_tenants.provisioning import provision


@shared_task
def onboard(slug):
    client = Client.objects.using("default").get(slug=slug)
    provision(client)
```

## Example: offboarding

```python
from django_db_tenants.provisioning import drop_database

client.status = Client.Status.SUSPENDED
client.save()
drop_database(client)
client.delete()
```

::: django_db_tenants.provisioning
