# Git workflow

Who is this for: contributors preparing commits and pull requests.

The repository is hosted at <https://github.com/GigiusB/django-db-tenants>; its main branch is `main`.

!!! note "Proposed conventions"
    The project has no recorded branching or commit conventions yet. The **Branches** and **Commits** sections below are the defaults this guide proposes; the pre-commit hooks are enforced by the repository.

## Branches

1. Update `main` and create a short-lived branch for one change:

    ```bash
    git switch main && git pull
    git switch -c fix/registry-invalidation
    ```

2. Commit on the branch; keep each commit focused on one concern, with its tests and documentation.
3. Before pushing, run the checks in [CI/CD and build](ci-cd.md#checks-a-change-must-pass).
4. Push the branch and open a pull request against `main`. GitHub Actions runs the full check on it ([CI/CD and build](ci-cd.md#github-actions)); merge only when **CI passed** is green.

Do not commit directly to `main`.

## Commits

- Write the subject in the imperative mood ("Add header resolver", not "Added"), at most about 72 characters, and explain the reason in the body when it is not obvious.
- Include in the same commit the code, the tests and the documentation pages the change affects (see [Contribution guidelines](contributing.md)).
- When `uv.lock` changes, commit it with the `pyproject.toml` change that caused it.

## Pre-commit hooks

`uv run pre-commit install` installs the hooks from `.pre-commit-config.yaml`; they run on the staged files at every commit. Run them on the whole tree with `uv run pre-commit run --all-files` or `uv run tox -e lint`.

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

A hook that changes files fails the commit; review the changes, stage them and commit again.

## Next steps

Run the full set of checks described in [CI/CD and build](ci-cd.md).
