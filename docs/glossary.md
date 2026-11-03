# Glossary

Terms used across the developer's guide, in alphabetical order.

## Client

The row in the [shared database](#shared-database) that describes one [tenant](#tenant): name, slug, status, [database strategy](#database-strategy) and its parameters. Model: `django_db_tenants.models.Client`. See the [Client model reference](development-guide/models/client.md).

## Config version

A string that changes every time a `Client` row is saved (`Client.config_version()`, built from `updated_at`). Each process compares it with the version it registered, and re-registers the tenant's connection when they differ. See [Runtime registration](development-guide/architecture.md#runtime-database-registration).

## Control host

A host name listed in `DB_TENANTS["CONTROL_HOSTS"]`. Requests to it get no tenant and are served from the [shared database](#shared-database), typically for the admin site (the control plane).

## Database strategy

The class that decides how a tenant's database is reached, created and dropped, chosen per client in `Client.db_strategy` (a django-strategy-field `StrategyField`) and configured by `Client.db_params`. The built-in one, `TemplateOverlay`, lays the client's parameters over the [template alias](#template-alias) connection. See [Database strategies](development-guide/api/strategies.md).

## Exempt path

A URL path prefix listed in `DB_TENANTS["EXEMPT_PATHS"]` (default `/healthz`). The middleware skips tenant resolution for it.

## Fernet

The symmetric encryption scheme from the `cryptography` package. The library uses it to encrypt `Client.db_params` (database passwords and other strategy secrets) at rest. See [Encryption](development-guide/api/encryption.md).

## IdP

Identity provider: the OpenID Connect server that authenticates a tenant's users (for example Entra ID, Okta, Keycloak).

## OIDC

OpenID Connect, the authentication layer on top of OAuth 2.0 that the optional `OidcStrategy` uses for per-tenant single sign-on. See [OIDC strategy](development-guide/api/oidc.md).

## Provisioning

Onboarding a client's database: create it (through the client's [database strategy](#database-strategy)), run migrations on it and mark the client `active`. Done by `provision()`, the `provision_tenant` command or the admin action. See [Provisioning](development-guide/api/provisioning.md).

## Resolver

A callable `resolver(request) -> Client | None` that tells the middleware which tenant a request belongs to. Set with `DB_TENANTS["RESOLVER"]`. See [Resolvers](development-guide/api/resolvers.md).

## RP-initiated logout

OpenID Connect logout started by the relying party (the Django site): after the local logout, the browser is sent to the IdP's `end_session_endpoint` so the IdP session ends too.

## Runtime registration

Adding a tenant's connection settings, built by the client's [database strategy](#database-strategy), to `django.db.connections` while the process runs, by `ensure_db_registered()`. See [Architecture](development-guide/architecture.md#runtime-database-registration).

## Shared apps

The Django apps listed in `DB_TENANTS["SHARED_APPS"]` (default: only `django_db_tenants`). Their tables live only in the [shared database](#shared-database).

## Shared database

The database behind the [template alias](#template-alias). It holds the client registry and, by default, a copy of the tenant-app tables for control-host logins.

## Template alias

The `DATABASES` alias (`DB_TENANTS["TEMPLATE_ALIAS"]`, default `"default"`) that is the [shared database](#shared-database) and the starting point of tenant connections: every [database strategy](#database-strategy) receives a copy of its settings, and the built-in `TemplateOverlay` lays the client's `db_params` over them.

## Tenant

A customer whose data lives in its own database. Represented by a [Client](#client) row; inside the code "tenant" and "client" name the same thing.

## Tenant alias

The `django.db.connections` alias of a tenant's database. It is always the client's `slug`.

## Tenant apps

Every installed app that is not a [shared app](#shared-apps), including `django.contrib.auth`, `sessions` and `contenttypes`. Their tables live in each [tenant database](#tenant-database).

## Tenant context

The tenant active for the running code, held in a `ContextVar`. Set by the middleware for a request, or by `tenant_context()` / `@with_tenant` for other code. The database router reads it. See [Context](development-guide/api/context.md).

## Tenant database

The database of one tenant, named by `Client.db_name` and reachable under the [tenant alias](#tenant-alias).
