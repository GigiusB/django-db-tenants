# Git workflow

Who is this for: contributors preparing commits and pull requests.

The repository is hosted at <https://github.com/GigiusB/django-db-tenants>; its main branch is `main`.

## Branches

Work happens on `develop`. `main` only receives releases, merged from `develop` by a maintainer: maintainers must follow the release process described in [`RELEASE.md`](https://github.com/GigiusB/django-db-tenants/blob/develop/RELEASE.md).

1. Update `develop` and create a short-lived branch for one change:

    ```bash
    git switch develop && git pull
    git switch -c fix/registry-invalidation
    ```

2. Commit on the branch; keep each commit focused on one concern, with its tests and documentation.
3. Before pushing, run the checks in [CI/CD and build](ci-cd.md#checks-a-change-must-pass).
4. Push the branch and open a pull request against `develop`. GitHub Actions runs the full check on it ([CI/CD and build](ci-cd.md#github-actions)); merge only when **CI passed** is green.

Do not commit directly to `main`.

## Commits

- Follow [Conventional Commits](https://www.conventionalcommits.org/): `<type>[(scope)][!]: <subject>`, for example `feat(resolvers): add a path-prefix resolver` or `fix: re-register the alias when db_params changes`. The `commitizen` hook rejects other messages, because the next version and the changelog are computed from them; `RELEASE.md` lists the types and what each does to the version.
- Write the subject in the imperative mood ("add header resolver", not "added"), at most about 72 characters including the type, and explain the reason in the body when it is not obvious.
- Include in the same commit the code, the tests and the documentation pages the change affects (see [Contribution guidelines](contributing.md)).
- When `uv.lock` changes, commit it with the `pyproject.toml` change that caused it.

## Pre-commit hooks

`uv run pre-commit install` installs the hooks from `.pre-commit-config.yaml`: the `commit-msg` hook checks the message, the others run on the staged files at every commit. Run them on the whole tree with `uv run pre-commit run --all-files` or `uv run tox -e lint`.

| Hook | Checks or fixes |
|---|---|
| `check-added-large-files`, `check-case-conflict`, `check-merge-conflict` | accidental large files, case clashes, conflict markers |
| `check-toml`, `check-yaml` | syntax of TOML and YAML files |
| `debug-statements`, `detect-private-key` | leftover `breakpoint()` / `pdb`, committed private keys |
| `end-of-file-fixer`, `mixed-line-ending` (LF), `trailing-whitespace` | whitespace |
| `validate-pyproject` | `pyproject.toml` against the packaging schemas |
| `uv-lock` | `uv.lock` matches `pyproject.toml` |
| `django-upgrade` (target Django 4.2) | rewrites outdated Django idioms |
| `ruff-check --fix`, `ruff-format` | lint rules and formatting from `ruff.toml` |
| `ty` | type checking (runs `uv run --frozen ty check` on the whole project) |
| `commitizen` (stage `commit-msg`) | the commit message follows Conventional Commits |
| `zensical-nav` | every page under `docs/` has an entry in the `nav` of `zensical.toml`, and every entry names an existing page (`tools/check_zensical_nav.py`; runs when a page or `zensical.toml` changes) |

A hook that changes files fails the commit; review the changes, stage them and commit again.

## Next steps

Run the full set of checks described in [CI/CD and build](ci-cd.md).
