# Testing strategy

Who is this for: contributors writing or running tests.

TL;DR: tests use real tenant databases, not mocks. Each tenant in a test gets a fresh database cloned from a template that is migrated once per session, on SQLite, PostgreSQL or MySQL. Use the `acme` / `globex` fixtures and `tenant_context()`.

## Run the tests

| Command | Runs |
|---|---|
| `uv run pytest` | the suite on the current Python and Django, SQLite |
| `TEST_DB=pg uv run pytest` | the same on PostgreSQL (connection from `.env`) |
| `TEST_DB=mysql uv run pytest` | the same on MySQL |
| `uv run pytest tests/test_router.py -k shared` | a subset |
| `uv run tox -p auto` | the whole matrix plus `lint`, `type` and `docs`, in parallel |
| `uv run tox -e py313-dj52-pg` | one environment: `<python>-<django>-<sqlite|pg|mysql>` |

tox environments run `pytest --cov --cov-report=term` by default; pass other pytest arguments after `--`: `uv run tox -e py313-dj52-sqlite -- -k strategy`.

## The matrix

From `tox.ini`:

| Django | Python | Databases |
|---|---|---|
| 4.2 | 3.11, 3.12 | sqlite, pg, mysql |
| 5.2 | 3.11, 3.15 | sqlite, pg, mysql |
| 6.0 | 3.12, 3.15 | sqlite, pg, mysql |
| 6.1 | 3.12, 3.15 | sqlite, pg, mysql |

Each server environment creates `test_<NAME>_<tox env>` so parallel runs against one server do not collide. PostgreSQL 15+ and MySQL 8.4+ cover every Django version in the matrix.

## Strictness

`pytest.toml` makes the suite fail on:

- any warning (`filterwarnings = error`), except one Django 5.x deprecation listed there;
- unknown markers (`--strict-markers`) and unknown configuration keys (`--strict-config`);
- an `xfail` test that passes (`xfail_strict`).

`tests/test_migrations.py` fails when a model change has no migration (`makemigrations --check` for `django_db_tenants` and the demo's `notes`).

## Test layout

| File | Covers |
|---|---|
| `test_context.py` | `tenant_context` with a slug or a client, nesting, reset on exceptions, unknown slugs |
| `test_db.py` | runtime registration, caching by config version, `force`, unregistering |
| `test_registry.py` | host and slug lookups, negative caching, invalidation, inactive clients |
| `test_router.py` | data isolation, shared apps, relations, `allow_relation`, `allow_migrate` |
| `test_middleware.py` | host and header resolution, ports, control hosts, exempt paths, 404s and the custom not-found handler |
| `test_cache.py` | `tenant_key_func` key formats, isolation between tenants, cache sessions, shared registry keys |
| `test_models.py` | `Client` validation (including `db_params`), `config_version()`, encryption at rest, legacy plain-text and undecryptable values |
| `test_strategies.py` | the strategy field and registry, `TemplateOverlay` settings, custom strategies, missing strategy classes, the admin form |
| `test_provisioning.py` | `provision()`, `drop_database()`, unsupported vendors, the `provision_tenant` (strategy and params options, bad input) and `migrate_tenants` commands |
| `test_tasks.py` | `with_tenant`, `for_each_tenant` |
| `test_demo.py` | end-to-end checks of the demo project: pages, logins, notes, tasks, `notes_report`, `seed_demo` |
| `test_migrations.py` | no missing migrations |

Shared helpers live in `tests/_extra/testutils` (importable as `testutils`); fixtures are registered as a pytest plugin by `tests/conftest.py`.

## Fixtures

| Fixture | Gives |
|---|---|
| `acme`, `globex` | an `active` client with a migrated database and the domain `<slug>.test` |
| `tenant_factory` | `tenant_factory("initech", domains=[...], migrated=True, **fields)`: more tenants, or an empty database with `migrated=False`. `fields` go to the client, so `db_strategy=` / `db_params=` pick another strategy; the database is still created by cloning, whatever the strategy |
| `tenant_db_name` | `tenant_db_name("acme")`: a name for a database the test creates itself (for example through `provision()`); dropped at the end of the test |
| `tenant_template_db` | name of the session-wide migrated template database |

Two fixtures run automatically:

- `_reset_tenant_state` calls `reset_tenant_state()` before and after each test: it unregisters the tenant aliases, clears every cache and the cached Fernet key.
- `_allow_tenant_connections` lets tests that use the database open connections to tenant aliases. Django 6.1 refuses connections to aliases not declared in `TestCase.databases`; tenant aliases are registered after that check, so the fixture lets through exactly the aliases created by `ensure_db_registered`.

The test settings (`testutils.settings`) add a control host, `control.test`, a fixed `ENCRYPTION_KEY`, and register `testutils.strategies.EnvironmentPassword` through `DATABASE_STRATEGIES`. Custom strategies used in tests must live in an importable module such as `testutils.strategies`, not in a test file: the field stores their dotted path.

## Isolation: how tenant databases work in tests

The shared database is handled by pytest-django as usual: each test runs in a transaction that is rolled back.

Tenant databases are **not** wrapped in that transaction. Each test gets new ones, which are dropped when it ends:

| Backend | Tenant database | Cloned from the template by |
|---|---|---|
| SQLite | a file in the test's `tmp_path` | file copy |
| PostgreSQL | `test_tenant_<slug>_<random>` | `CREATE DATABASE ... TEMPLATE` |
| MySQL | `test_tenant_<slug>_<random>` | table-by-table copy (MySQL has no templates) |

Server accounts therefore need the right to create and drop databases.

## Write a test

```python
from notes.models import Note
from testutils.factories import NoteFactory, UserFactory

from django_db_tenants import tenant_context


def test_notes_are_per_tenant(client, acme, globex):
    with tenant_context(acme):
        NoteFactory.create(author=UserFactory.create())
    with tenant_context(globex):
        assert not Note.objects.exists()
    assert client.get("/whoami/", HTTP_HOST="acme.test").json()["tenant"] == "acme"
```

Guidelines:

- **Create tenant-app objects inside `tenant_context()`.** Factories for users and notes write wherever the router points. `ClientFactory` and `ClientDomainFactory` always write to the shared database.
- **Choose the tenant with the host.** Pass `HTTP_HOST="<slug>.test"` to the test client; `control.test` is the control host.
- **Log in on a tenant** with `testutils.tenants.tenant_login(client, acme, user)`: the session must be stored in the tenant database.
- **Use the factories' explicit methods** (`.create()`, `.build()`, `.create_batch()`): they are typed. `ClientFactory` has the traits `provisioning` and `suspended`, for example `ClientFactory.create(suspended=True)`.
- **Freeze time** with `freezegun` for anything time-based: cache TTLs, `updated_at`-driven re-registration.
- Tests that need SQLite files (the demo's seeding) are skipped on other backends with `skipif(selected_backend() != "sqlite")`.

## Coverage

```bash
uv run pytest --cov --cov-report=term
```

`.coveragerc.toml` measures the `django_db_tenants` package with branch coverage, shows missing lines and hides fully covered files. Under tox each environment writes its own data file (`COVERAGE_FILE={env_dir}/.coverage`).

## Next steps

See which checks a change must pass in [CI/CD and build](ci-cd.md).
