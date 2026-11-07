# CI/CD and build

Who is this for: contributors checking a change before review, and maintainers building releases.

TL;DR: GitHub Actions runs the same tox environments you run locally, on every pull request and every push to `main`. Run `uv run tox -p auto` before pushing and CI holds no surprises. A second workflow publishes this site from `develop`.

## GitHub Actions

The workflow is `.github/workflows/ci.yml` (**CI**). It runs on pull requests, on pushes to `main`, and on demand (**Actions > CI > Run workflow**). A newer push to the same branch cancels the run in progress.

| Job | Runs | Notes |
|---|---|---|
| `lint`, `type`, `docs` | `tox -e lint`, `tox -e type`, `tox -e docs` | `lint` caches the pre-commit environments, keyed on `.pre-commit-config.yaml` |
| `build` | `uv build`, then imports the wheel in a clean environment | Uploads `dist/` (sdist and wheel) as the `dist` artifact of the run |
| `<python>-<django>-sqlite` | the 8 SQLite test environments | |
| `<python>-<django>-pg` | the 8 PostgreSQL test environments | PostgreSQL 16 service container, `TEST_PG_*` set to match it |
| `<python>-<django>-mysql` | the 8 MySQL test environments | MySQL 8.4 service container, `TEST_MYSQL_*` set to match it; installs `libmysqlclient-dev` to build `mysqlclient` |
| **CI passed** | nothing | Fails when any job above failed or was cancelled |

Every job installs uv with `astral-sh/setup-uv` and runs tox through `uvx` with the versions `tox.ini` requires; uv downloads each Python interpreter of the matrix. Matrix jobs run with `fail-fast: false`, so one failing combination does not hide the others.

To require CI before merging, protect `main` in **Settings > Branches** and add **CI passed** as the only required status check: it covers every job, including any added to the matrix later.

!!! warning "Keep the workflow and tox.ini in step"
    The test matrix is written twice: in `env_list` of `tox.ini` and in the three `test-*` jobs of the workflow. When you add or remove a combination, change both. This lists what tox would run:

    ```bash
    uv run tox -l
    ```

Coverage is printed in each test job's log (`--cov-report=term`); it is not uploaded to a coverage service.

## Checks a change must pass

```bash
docker compose up -d --wait     # only for the pg and mysql environments
uv run tox -p auto              # everything, in parallel
```

| tox environment | What it runs | Fails on |
|---|---|---|
| `py<python>-dj<django>-<sqlite|pg|mysql>` | `pytest --cov --cov-report=term` on that combination | a failing test, a warning, a missing migration |
| `lint` | `pre-commit run --all-files --show-diff-on-failure` | any [hook](git-workflow.md#pre-commit-hooks): formatting, lint, lock file, YAML/TOML syntax, Django idioms |
| `type` | `ty check` | a type error in `src` or `tests` |
| `docs` | `zensical build --strict --clean` | a link to a missing page or anchor, an API page whose module does not exist, any Zensical warning |

The test matrix is listed in [Testing strategy](testing.md#the-matrix). A quick subset before pushing:

```bash
uv run tox -e py313-dj52-sqlite,lint,type,docs
```

tox installs its environments with uv (`tox-uv`) and the dependency groups from `pyproject.toml`; the test environments install the library itself plus the `postgres` or `mysql` extra matching the database.

## Build the package

```bash
uv build
```

This writes `dist/django_db_tenants-<version>.tar.gz` and `dist/django_db_tenants-<version>-py3-none-any.whl` with setuptools (`[build-system]` in `pyproject.toml`). Only `src/django_db_tenants` is packaged, with its `py.typed` marker and migrations.

Check the result in a clean environment:

```bash
uv run --isolated --no-project --with dist/django_db_tenants-*.whl \
    python -c "import django_db_tenants; print(django_db_tenants.__version__)"
```

## Build the documentation

```bash
uv run zensical serve           # live preview on http://127.0.0.1:8000/
uv run zensical build           # static site in site/ (git-ignored)
uv run tox -e docs              # strict build, as the check runs it
```

The site is built with [Zensical](https://zensical.org/), configured in `zensical.toml`: an explicit `nav` in the guide's reading order (a new page needs an entry there; the `zensical-nav` pre-commit hook checks it), API pages generated from docstrings by mkdocstrings (static analysis of `src/`, nothing is imported), Mermaid diagrams. Pages link each other with relative file links (`../api/settings.md#reference`); the build checks that every linked page and anchor exists.

## Publish the documentation

The **Docs** workflow (`.github/workflows/docs.yml`) builds the site and publishes it on GitHub Pages at <https://gigiusb.github.io/django-db-tenants/> (`site_url` in `zensical.toml`).

| Trigger | Effect |
|---|---|
| push to `develop` | build and publish |
| **Actions > Docs > Run workflow** with `develop` selected | build and publish again, for example after changing the Pages settings |
| any other branch, or a manual run on another branch | nothing: the jobs are skipped |

| Job | Does |
|---|---|
| `build` | `uv run --frozen --only-group docs zensical build --strict --clean`: only the `docs` dependency group, from `uv.lock`, without installing the project. Uploads `site/` as the Pages artifact |
| `deploy` | Publishes the artifact with `actions/deploy-pages`, in the `github-pages` environment; the run summary links to the site |

A failing strict build publishes nothing: the site online stays at the last good version. One deployment runs at a time; a newer push waits for the current one instead of cancelling it. Pull requests do not publish, but the `docs` job of the **CI** workflow builds the site on every pull request with the same strict check.

The "edit this page" links of the published site (`edit_uri`) point to `docs/` on `develop`.

### One-time repository setup

1. In **Settings > Pages > Build and deployment**, set **Source** to **GitHub Actions**.
2. In **Settings > Environments > github-pages > Deployment branches and tags**, allow `develop`. GitHub creates the environment allowing only the default branch, and refuses deployments from `develop` until it is added.
3. Push to `develop`, or run the workflow by hand.

## Releases

Release steps are in [Contribution guidelines](contributing.md#release-a-version).

## Next steps

Read the [Contribution guidelines](contributing.md).
