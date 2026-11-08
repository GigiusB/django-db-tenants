# Background tasks

The middleware never runs for Celery, RQ, cron jobs or management commands, so they start on the shared database. `django_db_tenants.tasks` gives them a tenant.

## One tenant per call: `@with_tenant`

The decorated function receives the tenant (a slug or a `Client`) as the `tenant` keyword or as its first positional argument; its body runs inside `tenant_context(tenant)`.

```python
from celery import shared_task
from django_db_tenants.tasks import with_tenant


@shared_task
@with_tenant
def send_invoices(tenant):
    Invoice.objects.filter(sent=False)  # the tenant's database


send_invoices.delay(tenant="acme")  # pass the slug: it serialises
```

Put `@with_tenant` under the task decorator, so the context is set when the worker runs the function. A `None` tenant runs the body on the shared database.

## Every tenant: `for_each_tenant`

```python
from django_db_tenants.tasks import for_each_tenant

counts = for_each_tenant(lambda client: Invoice.objects.count())
# {"acme": 12, "globex": 3}
```

`func(client)` runs inside each client's context; the result is a dict keyed by slug. Only `active` clients by default; `only_active=False` includes the others. Clients run one after the other, and an exception stops the loop.

The demo's `notes/tasks.py` and `notes_report` command use both helpers.

::: django_db_tenants.tasks
