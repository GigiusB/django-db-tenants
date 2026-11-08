# Development Guide

This guide is for engineers who work on django-db-tenants itself, and for developers who integrate it and need to know how it behaves inside.

## Map of the guide

| Page | What you find there |
|---|---|
| [Quick start](quick-start.md) | Clone, install, run the tests and the demo project in a few minutes |
| [Local environment setup](local-setup.md) | Toolchain, database servers, environment files, IDE settings |
| [Codebase structure](codebase-structure.md) | What each module and configuration file is for |
| [Design overview](design-overview.md) | The five pieces that make multi-tenancy work, and the trade-offs the design accepts |
| [Architecture](architecture.md) | How a request, a task or a command reaches the right database |
| [Model reference](models/index.md) | The data model, with an editable diagram, and one page per model |
| [CLI reference](cli/index.md) | Every management command and option |
| [API reference](api/index.md) | Settings, public functions and classes, module by module |
| [Testing strategy](testing.md) | Test layout, fixtures, database backends, the tox matrix |
| [Git workflow](git-workflow.md) | Branches, commits and the pre-commit hooks |
| [CI/CD and build](ci-cd.md) | The checks a change must pass, building the package and the docs |
| [Contribution guidelines](contributing.md) | Code standards, extension recipes, release steps |

## Next steps

Go to the [Quick start](quick-start.md).
