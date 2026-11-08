# Contributing to django-db-tenants

This page gets you from a fresh clone to a passing test run. The [developer's guide](https://gigiusb.github.io/django-db-tenants/) has the details: [Local environment setup](docs/development-guide/local-setup.md), [Testing strategy](docs/development-guide/testing.md), [Contribution guidelines](docs/development-guide/contributing.md) and [Git workflow](docs/development-guide/git-workflow.md).

## Prerequisites

| Tool | Why |
|---|---|
| [uv](https://docs.astral.sh/uv/) | Creates the virtual environment, installs the dependencies and runs every tool. It downloads the Python versions it needs (3.13 from `.python-version`, plus the tox matrix: 3.11, 3.12, 3.15) |
| [ruff](https://docs.astral.sh/ruff/) | Lints and formats the code (pre-commit hooks, `tox -e lint`) and formats the API signatures of the docs (`zensical`, `tox -e docs`). Installed by `uv sync`; no separate install needed |
| MySQL client headers | `mysqlclient` is built from source: `libmysqlclient-dev` on Debian/Ubuntu, `mysql-client` on Homebrew (see `.envrc.example`). Without them, use `uv sync --no-group db` and test MySQL through tox only |
| Docker with Compose | Optional: PostgreSQL and MySQL servers for the `pg` and `mysql` test backends. Any PostgreSQL 15+ / MySQL 8.4+ server works too |

## Set up

```bash
git clone https://github.com/GigiusB/django-db-tenants.git
cd django-db-tenants
uv sync                     # .venv with the library (editable) and the dev group: tests, ruff, ty, docs, tox
uv run pre-commit install   # ruff, ty, django-upgrade, uv-lock, ... and the commit message format, on every commit
```

For the PostgreSQL and MySQL backends:

```bash
docker compose up -d --wait  # PostgreSQL on 127.0.0.1:55432, MySQL on 127.0.0.1:53306
cp .env.example .env         # the test connections, matching the Compose services
```

Optionally, `cp .envrc.example .envrc && direnv allow` loads `.env` and activates `.venv` on `cd`.

## Test

```bash
uv run pytest                     # SQLite: no server needed
TEST_DB=pg uv run pytest          # PostgreSQL, connection from .env
TEST_DB=mysql uv run pytest       # MySQL, connection from .env
uv run pytest tests/test_middleware.py -k header  # a subset
```

Every tenant in a test gets a real database of its own, cloned from a template migrated once per session, and dropped when the test ends. The fixtures (`acme`, `globex`, `tenant_factory`, ...) and factories are in `tests/_extra/testutils`; see [Testing strategy](docs/development-guide/testing.md) to write new tests.

The full matrix and the other checks run through tox:

```bash
uv run tox -p auto                        # every Python × Django × database env, plus lint, type, docs
uv run tox -e py313-dj52-pg               # one env: <python>-<django>-<sqlite|pg|mysql>
uv run tox -e lint,type,docs              # pre-commit hooks, ty, strict docs build
```

The same checks one by one:

```bash
uv run ruff check --fix . && uv run ruff format .
uv run ty check
uv run zensical serve # the developer's guide on http://127.0.0.1:8000/, reloaded on every change
```

## Try the demo

```bash
cd tests/demo
uv run python manage.py migrate && uv run python manage.py seed_demo && uv run python manage.py runserver
```

Then open <http://acme.localhost:8000/> and log in as `alice` / `demo`. See [`tests/demo/README.md`](tests/demo/README.md).

## Send a change

Work on a branch, add tests, update the pages of `docs/` that describe what you changed, and run `uv run tox -p auto` (or at least `uv run tox -e py313-dj52-sqlite,lint,type,docs`) before opening a pull request against `develop`. Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (`feat: ...`, `fix: ...`); maintainers release as described in [RELEASE.md](RELEASE.md). The [Contribution guidelines](docs/development-guide/contributing.md) list the code standards and recipes for common changes.
