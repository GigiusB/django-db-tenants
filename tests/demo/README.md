# django-db-tenants demo

A small Django project showing how to use `django-db-tenants`. It is also the project
the test suite runs against (`testutils.settings` extends `demo.settings`).

| Path | What it shows |
|---|---|
| `demo/settings.py` | The settings the library needs (look for `# django-db-tenants`) |
| `demo/urls.py` | Mounting the per-tenant SSO views |
| `demo/views.py` | `request.tenant` / `get_current_tenant()`, an exempt health check |
| `notes/` | An ordinary app whose tables live in every tenant database |
| `notes/tasks.py` | Background jobs with `@with_tenant` and `for_each_tenant` |
| `notes/management/commands/seed_demo.py` | Onboarding tenants at runtime with `provision_tenant` |

## Run it

From the repository root:

```bash
uv sync
cd tests/demo
uv run python manage.py migrate            # shared database (var/control.sqlite3)
uv run python manage.py seed_demo          # tenants 'acme' and 'globex', one SQLite file each
uv run python manage.py createsuperuser    # optional: for the control-plane admin
uv run python manage.py runserver
```

Then open:

* <http://acme.localhost:8000/>: log in as `alice` / `demo`
* <http://globex.localhost:8000/>: log in as `bob` / `demo` (alice does not exist here)
* <http://localhost:8000/admin/>: control plane: manage clients, domains and SSO settings
* <http://acme.localhost:8000/whoami/>: which database served the request

Browsers resolve `*.localhost` to `127.0.0.1`, so no `/etc/hosts` changes are needed.
With curl, pass the host explicitly: `curl -H 'Host: acme.localhost' http://127.0.0.1:8000/whoami/`.

Other commands:

```bash
uv run python manage.py notes_report       # count notes in every tenant DB
uv run python manage.py migrate_tenants    # migrate all tenant DBs after adding a migration
uv run python manage.py tenant_shell acme  # Django shell with the 'acme' tenant active
```

Runtime data lives in `tests/demo/var/` (git-ignored; override with `DEMO_VAR_DIR`).
Delete it to start over.
