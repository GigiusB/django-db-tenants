# Codebase structure

Who is this for: contributors looking for the right place to make a change.

## Repository layout

```text
src/django_db_tenants/        the library (the only package that ships)
tests/                        pytest suite
tests/_extra/testutils/       test utilities, importable as `testutils`
tests/demo/                   example Django project, importable as `demo` and `notes`
docs/                         this site (mkdocs)
```

## The library: `src/django_db_tenants`

| Module | Responsibility | Reference |
|---|---|---|
| `__init__.py` | Public entry points: `get_current_tenant`, `get_current_tenant_alias`, `tenant_context`, `ensure_db_registered`; `__version__` | [API reference](../api/) |
| `apps.py` | `AppConfig` (`label = "django_db_tenants"`, `BigAutoField`); connects the signal handlers and registers `DATABASE_STRATEGIES` in `ready()` | |
| `conf.py` | `DB_TENANTS` settings with defaults; dotted paths are imported on access | [Settings](../api/settings/) |
| `context.py` | The [tenant context](../../glossary/#tenant-context) (`ContextVar`) and `tenant_context()` | [Context](../api/context/) |
| `middleware.py` | `TenantMiddleware`: resolves the tenant of each request, sync and async | [Middleware](../api/middleware/) |
| `resolvers.py` | `resolve_by_host`, `resolve_by_header` | [Resolvers](../api/resolvers/) |
| `router.py` | `TenantRouter`: shared apps to the shared database, the rest to the active tenant | [Router](../api/router/) |
| `db.py` | [Runtime registration](../../glossary/#runtime-registration) of tenant connections | [Database registration](../api/db/) |
| `strategies.py` | [Database strategies](../../glossary/#database-strategy): `DatabaseStrategy`, the built-in `TemplateOverlay` (connection settings, create and drop per backend), the strategy `registry` | [Database strategies](../api/strategies/) |
| `registry.py` | Cached `Client` lookups by host and by slug, cache invalidation | [Registry](../api/registry/) |
| `signals.py` | Invalidates the registry cache and unregisters connections when `Client` / `ClientDomain` rows change | [Architecture](../architecture/#client-lookup-cache-and-invalidation) |
| `models.py` | `Client`, `ClientDomain` | [Model reference](../models/) |
| `fields.py`, `crypto.py` | `EncryptedTextField`, `EncryptedJSONField` and the Fernet helpers behind them | [Encryption](../api/encryption/) |
| `provisioning.py` | `create_database`, `migrate_tenant`, `provision`, `drop_database`, delegating to the strategy | [Provisioning](../api/provisioning/) |
| `tasks.py` | `with_tenant`, `for_each_tenant` for background work | [Background tasks](../api/tasks/) |
| `cache.py` | `tenant_key_func`: per-tenant cache key namespaces | [Cache isolation](../api/cache/) |
| `exceptions.py` | `TenantError`, `TenantNotFound`, `TenantInactive` | [Exceptions](../api/exceptions/) |
| `admin.py` | `ClientAdmin` with the domain inline and the provisioning action | [Admin](../api/admin/) |
| `sso/` | Per-tenant OpenID Connect: Authlib clients (`oidc.py`), claims-to-user mapping (`sync.py`), views and URLs | [SSO](../api/sso/) |
| `management/commands/` | `provision_tenant`, `migrate_tenants`, `tenant_shell` | [CLI reference](../cli/) |
| `migrations/` | Schema of `Client` and `ClientDomain` (shared database only). `0002`/`0003` moved the connection columns into `db_params` | |
| `py.typed` | Marks the package as typed (PEP 561) | |

### How the modules depend on each other

```mermaid
flowchart LR
    middleware --> resolvers --> registry --> models
    middleware --> db
    db --> strategies
    provisioning --> strategies
    models --> strategies
    middleware --> context
    router --> context
    cache --> context
    context -. lazy import .-> db
    context -. lazy import .-> registry
    tasks --> context
    provisioning --> db
    signals --> registry
    signals --> db
    models --> fields --> crypto
    registry --> cache
```

Every module reads its settings through `conf.app_settings`. `context.py` imports `db` and `registry` inside `tenant_context()` because `registry` imports the models, which must not load before the app registry is ready.

## Test utilities: `tests/_extra/testutils`

| Module | Contents |
|---|---|
| `settings.py` | Test settings: the demo's settings plus the selected database backend, a fast password hasher, a tenant-namespaced `LocMemCache`, a fixed `ENCRYPTION_KEY`, `CONTROL_HOSTS = ["control.test"]` |
| `databases.py` | `TEST_DB` backend selection and `.env` loading |
| `plugin.py` | pytest fixtures: `tenant_factory`, `acme`, `globex`, `tenant_db_name`, `tenant_template_db`, plus two autouse fixtures |
| `tenants.py` | Creating, cloning and dropping tenant databases per backend; `reset_tenant_state()`, `tenant_login()` |
| `factories.py` | factory_boy factories: `ClientFactory`, `ClientDomainFactory`, `UserFactory`, `NoteFactory` |
| `sso.py` | `FakeOIDCClient`, a stand-in for the Authlib client in SSO view tests |
| `strategies.py` | `EnvironmentPassword`, a custom database strategy registered by the test settings, and `Unregistered`, one that is not |

See [Testing strategy](../testing/) for how they fit together.

## Demo project: `tests/demo`

| Path | What it shows |
|---|---|
| `demo/settings.py` | Every setting the library needs, marked `# django-db-tenants` |
| `demo/urls.py` | Mounting the SSO views under `sso/` |
| `demo/views.py` | `request.tenant`, `get_current_tenant()`, a health check on an [exempt path](../../glossary/#exempt-path) |
| `notes/` | An ordinary app whose tables live in every tenant database |
| `notes/tasks.py` | Background jobs with `@with_tenant` and `for_each_tenant` |
| `notes/management/commands/seed_demo.py` | Onboarding tenants with `provision_tenant` |
| `notes/management/commands/notes_report.py` | Reading every tenant database from one command |

## Configuration files

| File | Configures |
|---|---|
| `pyproject.toml` | Package metadata, runtime dependencies (Django, Authlib, requests, cryptography, django-strategy-field) and extras (`postgres`, `mysql`), dependency groups, setuptools package discovery |
| `uv.lock` | Locked versions of every dependency; kept current by the `uv-lock` hook |
| `ruff.toml` | Lint rules and formatting (line length 120, target Python 3.11) |
| `ty.toml` | Type checking: Python 3.11, extra import paths, per-file overrides |
| `pytest.toml` | pytest and pytest-django: test paths, Python path, settings module, strict options, warnings as errors |
| `.coveragerc.toml` | coverage.py: source package, branch coverage, report options |
| `tox.ini` | The Python × Django × database matrix plus `lint`, `type` and `docs` |
| `.github/workflows/ci.yml` | GitHub Actions: every tox environment, the package build ([CI/CD and build](../ci-cd/#github-actions)) |
| `.github/workflows/docs.yml` | GitHub Actions: builds this site from `develop` and publishes it on GitHub Pages ([Publish the documentation](../ci-cd/#publish-the-documentation)) |
| `.pre-commit-config.yaml` | Git hooks |
| `mkdocs.yml` | This site |
| `docker-compose.yml` | PostgreSQL and MySQL for the server test backends |
| `.env.example`, `.envrc.example` | Templates for the local environment files |
| `.editorconfig` | Indentation, line endings, final newline |
| `.python-version` | Python version uv uses for the project environment (3.13) |

## Next steps

See how the pieces work together at runtime in [Architecture](../architecture/).
