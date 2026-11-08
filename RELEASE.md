# Releasing django-db-tenants

Maintainers release with [Commitizen](https://commitizen-tools.github.io/commitizen/): the version comes from the commit history, never from a hand edit. Versions are bumped on `develop`; `main` only receives tagged releases, merged from `develop`.

```text
develop  ──●──●──●──[bump: 0.1.0 → 0.2.0]──●──●──
                         │ tag v0.2.0
main     ──●─────────────●  (merge of develop; the tag push creates the GitHub release)
```

## Every day, on `develop`

Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/): `<type>[(scope)][!]: <subject>`. The `commitizen` hook (stage `commit-msg`, installed by `uv run pre-commit install`) rejects any other message.

| Type | Use for | Next version |
|---|---|---|
| `feat` | a new feature | minor |
| `fix` | a bug fix | patch |
| `docs`, `refactor`, `perf`, `test`, `build`, `ci`, `style`, `chore` | anything else | no bump on their own |
| `feat!`, `fix!`, ... or a `BREAKING CHANGE:` footer | an incompatible change | major (minor while the version is `0.x`) |

```text
feat(resolvers): resolve the tenant from a path prefix

fix: re-register the alias when db_params changes

refactor!: rename DB_TENANTS["CACHE_ALIAS"] to "REGISTRY_CACHE"

BREAKING CHANGE: projects that set CACHE_ALIAS must rename the key.
```

The subject stays imperative, and the body explains why, as before. `uv run cz commit` writes the message interactively, but it is optional. `feat` and `fix` commits appear in `CHANGELOG.md`, so write their subjects for the library's users.

## Release a version

1. Bump on an up-to-date `develop`, after `uv run tox -p auto` passes:

    ```bash
    git switch develop && git pull
    uv run cz bump --dry-run   # shows the next version and its changelog entry
    uv run cz bump             # writes the version, updates CHANGELOG.md, commits, tags
    ```

    `cz bump` reads the commits since the last tag, picks the increment from their types (table above), and makes one commit, `bump: version 0.1.0 → 0.2.0`, that updates:

    - `version` in `pyproject.toml`;
    - `__version__` in `src/django_db_tenants/__init__.py`;
    - the project's entry in `uv.lock`;
    - `CHANGELOG.md`, with a new section for the version.

    It then creates the annotated tag `v0.2.0` on that commit. Read the changelog entry before going on; to start over, see [Undo a bump](#undo-a-bump).

2. Push `develop` **without** the tag, and open a pull request from `develop` to `main`:

    ```bash
    git push origin develop
    gh pr create --base main --head develop --title "Release v0.2.0" --body-file <(awk '/^## /{n++} n==1' CHANGELOG.md)
    ```

3. When **CI passed** is green, merge with **Create a merge commit**, never with squash or rebase. Or locally, where a fast-forward is enough:

    ```bash
    git switch main && git pull && git merge --ff-only develop && git push origin main
    ```

4. Push the tag:

    ```bash
    git push origin v0.2.0
    ```

    The **Release** workflow (`.github/workflows/release.yml`) checks that the tag is in `main`'s history and matches the version in `pyproject.toml`, builds the sdist and wheel, and creates the GitHub release with the files and the version's `CHANGELOG.md` section as notes.

Publishing to PyPI is not configured yet. Until it is, upload the release's files by hand: `uv build && uv publish`, from a checkout of the tag.

## Rules that keep this working

- **Never squash or rebase `develop` into `main`.** Both create new commits: the tag would no longer be in `main`'s history (the Release workflow refuses it), and the squashed message loses the `feat:` / `fix:` lines the next bump and changelog are computed from.
- **`main` only receives merges from `develop`.** A hotfix is a `fix:` commit on `develop`, released as a patch version through the normal steps. When a fix has to go on `main` directly, merge `main` back into `develop` at once, or the next bump will not see it and the branches drift apart.
- **Bump on `develop`, not on `main`.** Bumping on `main` after the merge would also work, but then the bump commit and tag live on `main`, and every release needs a merge from `main` back into `develop`. A CI job that bumps on `main` has the same problem, plus bot commits on a protected branch.
- **Push the tag after the merge, not with `develop`.** The tag push creates the release, so pushing it early (`git push --follow-tags`) releases code that `main` does not have yet; the Release workflow fails on such a tag.

## Undo a bump

Before anything is pushed, drop the commit and the tag, fix the history (for example reword a commit with the wrong type), and bump again:

```bash
git tag -d v0.2.0
git reset --hard HEAD~1
```

After the tag is pushed, do not move it: release a new patch version instead.

## Configuration

| Where | What |
|---|---|
| `[tool.commitizen]` in `pyproject.toml` | Conventional Commits rules; the `uv` version provider (`project.version` and `uv.lock`); `version_files` for `__version__`; tags `v<version>`, annotated; changelog updated on every bump; `major_version_zero` |
| `release` dependency group in `pyproject.toml` | Commitizen, installed by `uv sync` through the `dev` group |
| `.pre-commit-config.yaml` | The `commitizen` hook on `commit-msg` (`default_install_hook_types` installs both hook types) |
| `.github/workflows/release.yml` | The GitHub release, on every pushed `v*` tag |
| `CHANGELOG.md` | Written by `cz bump`; do not edit the generated sections by hand |

History before `v0.1.0` does not follow Conventional Commits. The `v0.1.0` tag on `main` is the starting point: `cz bump` and the changelog only read the commits after it.
