# Quick start

Who is this for: a developer with a fresh clone who wants passing tests and a running multi-tenant demo, using SQLite only.

TL;DR:

```bash
uv sync && uv run pytest
cd tests/demo && uv run python manage.py migrate && uv run python manage.py seed_demo && uv run python manage.py runserver
```

## Prerequisites

- [uv](https://docs.astral.sh/uv/). It installs the Python version pinned in `.python-version` (3.13) when it is missing.
- The MySQL client headers (`libmysqlclient-dev` or your platform's equivalent). `uv sync` builds `mysqlclient` from the `db` dependency group; see [Local environment setup](../local-setup/#install-the-dependencies) to skip it.

## 1. Install

```bash
git clone https://github.com/GigiusB/django-db-tenants.git
cd django-db-tenants
uv sync
```

`uv sync` creates `.venv` with the library in editable mode plus the `dev` dependency group (tests, linters, database drivers, docs, tox).

## 2. Run the tests

```bash
uv run pytest
```

The suite runs on SQLite and needs no server. Every tenant in a test gets a real database of its own; see [Testing strategy](../testing/).

## 3. Run the demo project

The demo in `tests/demo` is a small Django project that uses the library. It is also the project the test suite runs against.

```bash
cd tests/demo
uv run python manage.py migrate            # shared database: tests/demo/var/control.sqlite3
uv run python manage.py seed_demo          # tenants 'acme' and 'globex', one SQLite file each
uv run python manage.py runserver
```

`seed_demo` calls the [`provision_tenant`](../cli/provision-tenant/) command for each tenant, then creates one user in each tenant database.

## 4. See the routing work

Open these addresses. Browsers resolve `*.localhost` to `127.0.0.1`, so no `/etc/hosts` change is needed.

| Address | What you see |
|---|---|
| <http://acme.localhost:8000/> | ACME's site. Log in as `alice` / `demo` |
| <http://globex.localhost:8000/> | Globex's site. Log in as `bob` / `demo`; `alice` does not exist here |
| <http://acme.localhost:8000/whoami/> | JSON with the tenant that served the request and its user count |
| <http://localhost:8000/admin/> | The control plane (a [control host](../../glossary/#control-host)); create a superuser first with `uv run python manage.py createsuperuser` |

With curl, pass the host explicitly:

```bash
curl -H 'Host: acme.localhost' http://127.0.0.1:8000/whoami/
# {"tenant": "acme", "users": 1}
```

Other commands to try from `tests/demo`:

```bash
uv run python manage.py notes_report       # count notes in every tenant database
uv run python manage.py migrate_tenants    # migrate every tenant database
uv run python manage.py tenant_shell acme  # Django shell with 'acme' active
```

Runtime data lives in `tests/demo/var/` (git-ignored; set `DEMO_VAR_DIR` to move it). Delete the directory to start over.

## Next steps

- Read [Architecture](../architecture/) to see what happened behind each of those requests.
- Set up PostgreSQL and MySQL for the full test matrix in [Local environment setup](../local-setup/).
