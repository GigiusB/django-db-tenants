# Database registration

`django_db_tenants.db` adds tenant connections to `django.db.connections` while the process runs. See [Runtime database registration](../architecture.md#runtime-database-registration) for the mechanism.

## Use it

The middleware, `tenant_context()` and the provisioning functions call `ensure_db_registered()` for you. Call it yourself to use `.using()` or `connections[...]` directly:

```python
from django.db import connections
from django_db_tenants import ensure_db_registered
from django_db_tenants.registry import get_client

alias = ensure_db_registered(get_client("acme"))  # "acme"
with connections[alias].cursor() as cursor:
    cursor.execute("SELECT count(*) FROM auth_user")
```

| Function | Effect |
|---|---|
| `ensure_db_registered(client, force=False)` | Registers `client.slug` with the settings returned by the client's [database strategy](strategies.md), unless this process already has it at the same config version. `force=True` re-registers anyway. Returns the alias |
| `is_registered(alias)` | Whether the alias is in `connections.settings` (for any reason, including aliases from `DATABASES`) |
| `unregister_db(alias)` | Closes this thread's connection for the alias and removes it from this process |

Registration is per process and thread-safe; closing the connection only affects the calling thread. Other threads drop their connection at the end of their request, as usual.

::: django_db_tenants.db
