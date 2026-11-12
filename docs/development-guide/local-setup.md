# Local environment setup

Who is this for: contributors who need the whole toolchain, including the PostgreSQL and MySQL test backends. For SQLite only, the [Quick start](quick-start.md) is enough.

## Prerequisites

| Tool | Why | Notes |
|---|---|---|
| [uv](https://docs.astral.sh/uv/) | Python, virtual environment, dependencies, running every tool | Installs Python 3.13 from `.python-version` when missing |
| Python 3.11 or newer | Supported range starts at 3.11 (`requires-python = ">=3.11"`) | tox also needs the interpreters of the matrix (3.11, 3.12, 3.15); uv downloads them |
| MySQL client headers | `mysqlclient` is compiled on install | `libmariadb-dev` (or `libmysqlclient-dev`) on Debian/Ubuntu, `mysql-devel` or `mariadb-connector-c-devel` elsewhere |
| Docker with Compose | Optional: PostgreSQL and MySQL servers for the `pg` and `mysql` test environments | Any PostgreSQL 15+ / MySQL 8.4+ server works too |
| [direnv](https://direnv.net/) | Optional: loads `.env` and activates `.venv` on `cd` | See [Environment files](#environment-files) |

## Install the dependencies

```bash
uv sync
```

This installs the library in editable mode and the `dev` dependency group, which includes the other groups defined in `pyproject.toml`:

| Group | Contents | Used by |
|---|---|---|
| `test` | pytest, pytest-django, pytest-cov, factory-boy, freezegun | `pytest`, every tox test environment |
| `lint` | ruff, ty, django-stubs, pre-commit | `tox -e lint`, `tox -e type`, the git hooks |
| `db` | psycopg, mysqlclient | plain `pytest` runs with `TEST_DB=pg` or `TEST_DB=mysql` |
| `docs` | zensical, mkdocstrings, ruff (mkdocstrings formats the API signatures with it) | `zensical serve`, `tox -e docs` |
| `dev` | all of the above plus tox and tox-uv | `uv sync` (default group) |

Without the MySQL headers, skip the `db` group and work on SQLite and PostgreSQL through tox:

```bash
uv sync --no-group db
```

## Install the git hooks

```bash
uv run pre-commit install
```

The hooks run on every commit. The list is in [Git workflow](git-workflow.md#pre-commit-hooks).

## Start the database servers

`docker-compose.yml` defines PostgreSQL 16 and MySQL 8.4, published on `127.0.0.1:55432` and `127.0.0.1:53306` so they do not clash with servers on the default ports. Their data lives in `tmpfs` and disappears when the containers stop.

```bash
docker compose up -d --wait
cp .env.example .env
```

## Environment files

### `.env`

The test settings read the database connections from `.env` at the project root (variables already in the environment win). `.env.example` matches the Compose services:

| Variable | Default in `.env.example` | Meaning |
|---|---|---|
| `TEST_DB` | unset (`sqlite`) | Backend for plain `pytest` runs: `sqlite`, `pg` or `mysql`. tox sets it from the environment name |
| `TEST_PG_HOST`, `TEST_PG_PORT` | `127.0.0.1`, `55432` | PostgreSQL server |
| `TEST_PG_USER`, `TEST_PG_PASSWORD` | `tenants`, `tenants` | Account allowed to create and drop databases |
| `TEST_PG_NAME` | `django_db_tenants` | Base name; tests use `test_<NAME>`, or `test_<NAME>_<tox env>` under tox |
| `TEST_MYSQL_HOST`, `TEST_MYSQL_PORT` | `127.0.0.1`, `53306` | MySQL server |
| `TEST_MYSQL_USER`, `TEST_MYSQL_PASSWORD` | `root`, `tenants` | Account allowed to create and drop databases |
| `TEST_MYSQL_NAME` | `django_db_tenants` | Base name; tests use `test_<NAME>`, or `test_<NAME>_<tox env>` under tox |

`HOST`, `PORT` and `USER` are required for a server backend; `NAME` falls back to `django_db_tenants` and `PASSWORD` to an empty string (`tests/_extra/testutils/databases.py`).

`.env.example` also lists optional, commented-out variables. The test suite ignores them; they apply only when `.env` is exported into your shell, for example by [direnv](#envrc-direnv):

| Variable | Default | Meaning |
|---|---|---|
| `DEMO_VAR_DIR` | `tests/demo/var` | Directory of the demo project's SQLite files (use an absolute path) |
| `DJANGO_SECRET_KEY` | an insecure demo key | `SECRET_KEY` of the demo project |
| `DJANGO_DEBUG` | `1` | `1` turns the demo's `DEBUG` on, anything else off |
| `ENCRYPTION_KEY` | a fixed demo key | Fernet key for the demo's stored secrets |
| `UV_LINK_MODE` | unset | `copy` silences uv's hardlink warning when its cache is on another filesystem |

Keep comments on their own lines in `.env`: values are read up to the end of the line.

### `.envrc` (direnv)

```bash
cp .envrc.example .envrc
direnv allow
```

`.envrc.example` loads `.env` (or the file named by `ENVFILE`), adds `./src` to `PYTHONPATH` and activates `.venv`. It stops with a message when `.venv` or the env file is missing.

## Check the setup

```bash
uv run pytest                     # SQLite
TEST_DB=pg uv run pytest          # PostgreSQL from .env
TEST_DB=mysql uv run pytest       # MySQL from .env
uv run ty check                   # types
uv run pre-commit run --all-files # every lint hook
uv run zensical build --strict    # this site
```

## Configure your IDE

- Interpreter: `.venv/bin/python`.
- Source roots: `src`, `tests/_extra` (the `testutils` package) and `tests/demo` (the `demo` and `notes` packages). pytest gets the same paths from `pythonpath` in `pytest.toml`, ty from `extra-paths` in `ty.toml`, ruff from `src` in `ruff.toml`.
- Django settings for test runs: `testutils.settings`. pytest-django reads it from `pytest.toml`.
- Formatting: ruff (line length 120). `.editorconfig` sets the indentation and line endings for other files.

## Preview the docs

```bash
uv run zensical serve
```

The site reloads on every change under `docs/`, `zensical.toml` and `src/` (the API pages are generated from docstrings).

## Next steps

Learn the layout in [Codebase structure](codebase-structure.md).
