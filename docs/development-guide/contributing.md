# Contribution guidelines

Who is this for: anyone sending a change to django-db-tenants.

## Checklist for every change

1. Discuss larger changes in an issue first.
2. Work on a branch ([Git workflow](git-workflow.md)).
3. Add or update tests; they must pass on SQLite, PostgreSQL and MySQL ([Testing strategy](testing.md)).
4. Update the pages of this guide that describe what you changed, in the same change (see [Keep the docs in sync](#keep-the-docs-in-sync)).
5. Run `uv run tox -p auto`, or at least `uv run tox -e py313-dj52-sqlite,lint,type,docs` ([CI/CD and build](ci-cd.md)).

## Code standards

| Topic | Rule | Enforced by |
|---|---|---|
| Python | Code must run on Python 3.11 and newer (`requires-python`, ruff `target-version = "py311"`) | ruff, tox matrix |
| Django | Code must run on Django 4.2, 5.2, 6.0 and 6.1 | tox matrix, `django-upgrade --target-version 4.2` |
| Databases | Features must work on SQLite, PostgreSQL and MySQL, or fail with a clear error (as `TemplateOverlay.create_database` does with `NotImplementedError`) | tox matrix |
| Style | ruff format, line length 120; rules E, W, F, I, B, UP, DJ, BLE, C4, PIE, PT, SIM, RET, T20, RUF, S | `ruff.toml`, pre-commit |
| Imports | isort order with `django_db_tenants`, `testutils`, `demo`, `notes` as first-party | ruff `I` |
| Types | The package ships `py.typed`; new public functions get type hints | `ty check` |
| Logging | Use the module logger (`logging.getLogger(__name__)`), never `print` | ruff `T20` |
| Settings | Every option goes through `DB_TENANTS` and `conf.app_settings`; an optional module uses its own sub-dict (`DB_TENANTS["OIDC"]`, read by `oidc.conf.oidc_settings`); no new top-level Django settings | review |
| Security | Secrets in models use `EncryptedTextField` or `EncryptedJSONField`; redirects are checked with `url_has_allowed_host_and_scheme` | ruff `S`, review |

Silence a lint rule only on the line that needs it, with the rule code and a reason: `# noqa: BLE001 - report per tenant and continue`.

## Recipes

### Change a model

1. Edit `src/django_db_tenants/models.py`.
2. Generate the migration from the demo project, which has the library installed:

    ```bash
    cd tests/demo && uv run python manage.py makemigrations django_db_tenants
    ```

3. Update the [Model reference](models/index.md) page and the [data-model diagram](models/index.md#edit-the-diagram).
4. `tests/test_migrations.py` fails until the migration exists.

Remember that library models live in the shared database only; they must not be referenced by foreign keys from tenant apps.

### Add a setting

1. Add the key and its default, with a comment, to `DEFAULTS` in `conf.py`. If the value is a dotted path to a callable, add the key to the `import_strings` given to `AppSettings` (`app_settings = AppSettings(DEFAULTS, frozenset({...}))`).
2. Read it with `app_settings.<KEY>` at the point of use (not at import time), so `override_settings` works in tests.
3. Test both the default and an override.
4. Add a row to the [Settings](api/settings.md) reference.

### Add a resolver

1. Add a function `(request) -> Client | None` to `resolvers.py`. Use the cached lookups in `registry.py`; raise `TenantNotFound` / `TenantInactive` to refuse a request.
2. Test it through the middleware with `override_settings(DB_TENANTS={..., "RESOLVER": ...})`, as `test_middleware.py` does for `resolve_by_header`.
3. Document it on the [Resolvers](api/resolvers.md) page.

### Add a management command

1. Add `management/commands/<name>.py` with a `Command(BaseCommand)`; give every argument a `help` text.
2. Query library models with `.using(app_settings.TEMPLATE_ALIAS)`; switch tenants with `tenant_context()` or `for_each_tenant()`.
3. Make failures visible in the exit status, as `migrate_tenants` does.
4. Test it with `call_command` (see `test_provisioning.py`).
5. Add a page to the [CLI reference](cli/index.md) (`docs/development-guide/cli/<name>.md`); the navigation picks it up from the file layout.

### Add a database strategy

1. Subclass `DatabaseStrategy` (or `TemplateOverlay`) in `strategies.py` for a built-in one, or in your project for a custom one. Declare `label` and `param_keys`; implement `connection_settings()`, and `create_database()` / `drop_database()` if it supports provisioning ([the contract](api/strategies.md#the-contract)).
2. Built-in: `registry.register(...)` it in `strategies.py`. Custom: list it in `DB_TENANTS["DATABASE_STRATEGIES"]`.
3. Test it like `test_strategies.py` does: a strategy used by tests must be importable by dotted path (put it in `testutils/strategies.py`).
4. Document it on [Database strategies](api/strategies.md).

Registering a strategy needs no migration.

### Support another database backend

1. Add a branch for the vendor to `TemplateOverlay.create_database()` and `drop_database()` in `strategies.py`.
2. Teach `tests/_extra/testutils/tenants.py` to create, clone and drop databases on it, and `testutils/databases.py` to configure it from `TEST_<BACKEND>_*` variables.
3. Add a service to `docker-compose.yml`, variables to `.env.example`, a factor to `tox.ini`, a `test-<backend>` job with a service container to `.github/workflows/ci.yml`, and an extra to `pyproject.toml`.
4. Update [Database strategies](api/strategies.md#templateoverlay) and [Local environment setup](local-setup.md).

### Add to the public API

1. Implement the function in its module, with type hints and a docstring: the docstring is published on the module's API page.
2. If it belongs to the stable surface, import it in `src/django_db_tenants/__init__.py` and list it in the module docstring there.
3. Document it on the module's page in [API reference](api/index.md); for a new module, add a page `docs/development-guide/api/<module>.md` with a `::: django_db_tenants.<module>` block, and a row in the module table of the API reference.

## Keep the docs in sync

| You changed | Update |
|---|---|
| A model or field | [Model reference](models/index.md) page, data-model diagram, migration |
| A `DB_TENANTS` key | [Settings](api/settings.md) |
| A database strategy, or `db_params` keys | [Database strategies](api/strategies.md), [Client](models/client.md) |
| A management command or option | [CLI reference](cli/index.md) page |
| A public function or class | its [API reference](api/index.md) page (docstring and text) |
| Request flow, routing, caching, registration | [Architecture](architecture.md) |
| Test fixtures or utilities | [Testing strategy](testing.md) |
| The tox matrix | `tox.ini` **and** `.github/workflows/ci.yml`, [Testing strategy](testing.md#the-matrix) |
| Tooling, tox, hooks, dependencies | [Local environment setup](local-setup.md), [CI/CD and build](ci-cd.md), [Git workflow](git-workflow.md) |
| A new term | [Glossary](../glossary.md) |

Link to other pages with relative site paths ending in `/` (for example `../api/settings/`), not with `.md` file names.

## Release a version

The version is written in two places, which must match:

- `version` in `pyproject.toml`;
- `__version__` in `src/django_db_tenants/__init__.py`.

Steps:

1. Update both values on a release branch, then run `uv lock` so the lock file records the new version.
2. Run the full check: `uv run tox -p auto`, and make sure **CI passed** is green on the release branch.
3. Build: `uv build`, and check the wheel as shown in [CI/CD and build](ci-cd.md#build-the-package). CI also builds both files on every run and keeps them as the `dist` artifact.
4. Merge to `main` and tag the merge commit, for example `git tag v0.2.0 && git push origin v0.2.0`.

No publishing to a package index is configured yet; uploading `dist/` (for example with `uv publish`) is a manual step for the maintainer.

## Next steps

Return to the [Development Guide](index.md) index.
