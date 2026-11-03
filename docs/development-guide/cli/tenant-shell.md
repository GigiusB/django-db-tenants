# tenant_shell

Open Django's interactive `shell` with a tenant active, so every query on tenant apps goes to that tenant's database.

Source: `src/django_db_tenants/management/commands/tenant_shell.py`.

## Synopsis

```text
python manage.py tenant_shell SLUG
```

## Arguments

| Argument | Type | Required | Effect |
|---|---|---|---|
| `SLUG` | positional, string | yes | Slug of the client to activate |

## Behaviour

- Looks the client up by slug through the registry cache, registers its database alias, prints `Tenant '<slug>' active.` and starts `shell` with its default options (the interface is chosen by Django: IPython, bpython or plain Python).
- The client's status is not checked: suspended and provisioning clients can be inspected.
- An unknown slug raises `TenantNotFound` before the shell starts, and the command exits with status `1`.
- Options of `shell` itself (`-c`, `-i`) are not available. For a one-off command, use `tenant_context()` in `shell -c`:

```bash
python manage.py shell -c "from django_db_tenants import tenant_context
from notes.models import Note
with tenant_context('acme'): print(Note.objects.count())"
```

## Example

```text
$ python manage.py tenant_shell acme
Tenant 'acme' active.
>>> from django.contrib.auth import get_user_model
>>> get_user_model().objects.values_list("username", flat=True)
<QuerySet ['alice']>
```

## See also

[`tenant_context()`](../api/context.md), which the command uses.
