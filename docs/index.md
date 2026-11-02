# django-db-tenants

Database-per-client multi-tenancy for Django, with tenant databases registered at runtime and per-tenant OpenID Connect single sign-on.

This site is the **developer's guide**. It is for:

- contributors who change, test and release the library;
- developers who integrate the library into a Django project and need to know how it works inside.

## What the library does

- One **shared database** holds the client registry. Every client (the [tenant](glossary/#tenant)) gets its **own database**, with its own `auth` users, sessions and application tables.
- Tenant databases are added to `django.db.connections` **while the process runs**, so adding, suspending or re-pointing a client never needs a restart.
- How each client's database is reached, created and dropped is **pluggable**: a [database strategy](glossary/#database-strategy) per client, configured by encrypted parameters. The built-in one derives tenant connections from the shared database's settings.
- Each client can sign its users in through its own **OpenID Connect** identity provider (Entra ID, Okta, Keycloak, Google and others), configured as data on the client row.

## Where to start

| You want to | Read |
|---|---|
| Get from a fresh clone to passing tests and a running demo | [Quick start](development-guide/quick-start/) |
| Set up a full workstation (PostgreSQL, MySQL, IDE, docs) | [Local environment setup](development-guide/local-setup/) |
| Understand how a request reaches the right database | [Architecture](development-guide/architecture/) |
| Look up a model, a command, a setting or a function | [Model reference](development-guide/models/), [CLI reference](development-guide/cli/), [API reference](development-guide/api/) |
| Send a change | [Contribution guidelines](development-guide/contributing/) |

The project's [README](https://github.com/GigiusB/django-db-tenants#readme) has the short integration recipe (settings, URLs, first tenant). Terms used across these pages are defined in the [glossary](glossary/).

## Build these docs

The published version, built from the `develop` branch, is at <https://gigiusb.github.io/django-db-tenants/>. To build it locally:

```bash
uv run mkdocs serve     # live preview on http://127.0.0.1:8000/
uv run tox -e docs      # strict build, as the docs check runs it
```

## Next steps

Start with the [Quick start](development-guide/quick-start/).
