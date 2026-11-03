# provision_tenant

Create or update a [client](../../../glossary/#client), attach its domains, create its database, migrate it and mark it `active`. No restart is needed: within `CACHE_TTL` seconds every worker serves the new domains.

Source: `src/django_db_tenants/management/commands/provision_tenant.py`.

## Synopsis

```text
python manage.py provision_tenant SLUG --name NAME --db-name DB_NAME
    [--domain DOMAIN ...]
    [--db-strategy DOTTED_PATH] [--db-params JSON]
    [--db-engine ENGINE] [--db-host HOST] [--db-port PORT] [--db-user USER] [--db-password PASSWORD]
    [--skip-create-db] [--skip-migrate]
```

## Arguments and options

| Argument | Type | Required | Default | Effect |
|---|---|---|---|---|
| `SLUG` | positional, string | yes | | Client slug, also the database alias. Looked up first: an existing client is updated |
| `--name` | string | yes | | `Client.name`. Always overwritten |
| `--db-name` | string | yes | | `Client.db_name`. Always overwritten |
| `--domain` | string, repeatable | no | none | Host names of the client. The first one becomes primary, the others are set to non-primary. Stored lower-cased |
| `--db-strategy` | dotted path | no | keep the stored one; `TemplateOverlay` for a new client | `Client.db_strategy`. Must be a [registered strategy](../../api/strategies/#registration) |
| `--db-params` | JSON object | no | none | Merged into the stored `Client.db_params`, key by key |
| `--db-engine`, `--db-host`, `--db-port`, `--db-user`, `--db-password` | string | no | `""` | Shortcuts that set the `db_params` keys `ENGINE`, `HOST`, `PORT`, `USER`, `PASSWORD` (the keys of the built-in strategy). Applied after `--db-params` |
| `--skip-create-db` | flag | no | off | Do not create the database (it already exists) |
| `--skip-migrate` | flag | no | off | Do not run migrations on the tenant database |

## Behaviour

1. Rejects an unregistered `--db-strategy` and a `--db-params` value that is not a JSON object.
2. Loads the client by slug from the [shared database](../../../glossary/#shared-database), or prepares a new one (not saved yet).
3. Sets `name` and `db_name`, and `db_strategy` when given. Merges `--db-params`, then the `--db-*` shortcuts, into the stored `db_params`: keys not mentioned keep their stored value.
4. Validates the client with `full_clean()`, which includes the strategy's check of `db_params`. A failure (reserved slug, invalid slug, unknown `db_params` key) stops the command before anything is saved.
5. Saves the client, then each `--domain` with `update_or_create`. A domain that belonged to another client is **moved** to this one.
6. Calls `provision()`: the strategy creates the database (unless `--skip-create-db`; an existing PostgreSQL or MySQL database is left as is), it is migrated (unless `--skip-migrate`), and the status becomes `active`. The status becomes `active` even with `--skip-migrate`.

With the built-in strategy, the database is created on the server and with the account of the tenant's own connection settings, which needs the right to create databases. Parameters you leave out inherit the template connection, so the simplest setup is many databases on one server with one role.

## Output and exit status

| Outcome | Output | Exit status |
|---|---|---|
| Success | `Created and provisioned tenant '<slug>'.` or `Updated and provisioned tenant '<slug>'.` | `0` |
| Invalid options or validation error | `CommandError: ...` naming the problem; nothing saved | `1` |
| Database creation or migration error | the exception and its traceback; the client row is already saved and stays in `provisioning` | `1` |

The command is idempotent: run it again to retry a failed provisioning or to change settings.

## Examples

Tenant on the template server, one domain:

```bash
python manage.py provision_tenant acme \
    --name "ACME S.p.A." \
    --domain acme.example.com \
    --db-name tenant_acme
```

Tenant on its own server, two domains, signing in through Entra ID with the optional [`OidcStrategy`](../../api/oidc/):

```bash
python manage.py provision_tenant globex \
    --name "Globex Corporation" \
    --domain globex.example.com --domain portal.globex.com \
    --db-name globex --db-host db2.internal --db-user globex --db-password "$GLOBEX_DB_PASSWORD" \
    --db-strategy django_db_tenants.oidc.OidcStrategy \
    --db-params '{"OPTIONS": {"sslmode": "require"},
                  "SSO": {"ISSUER": "https://login.microsoftonline.com/<tenant-id>/v2.0",
                          "CLIENT_ID": "...", "CLIENT_SECRET": "..."}}'
```

Tenant using a custom strategy (see [Write your own strategy](../../api/strategies/#write-your-own-strategy)):

```bash
python manage.py provision_tenant initech --name Initech --db-name initech \
    --db-strategy myproject.tenancy.EnvironmentPassword \
    --db-params '{"PASSWORD_ENV": "INITECH_DB_PASSWORD"}'
```

Register a client whose database already exists and is migrated:

```bash
python manage.py provision_tenant hooli --name Hooli --db-name hooli --skip-create-db --skip-migrate
```

The demo project's `seed_demo` command calls this command from Python:

```python
call_command("provision_tenant", "acme", name="ACME S.p.A.", domain=["acme.localhost"], db_name="var/acme.sqlite3")
```

!!! warning "Secrets on the command line"
    Values passed as options are visible in the process list and the shell history. Read them from environment variables as above, use a strategy that reads them from the environment, or set them afterwards in the admin.

## See also

- [Provisioning API](../../api/provisioning/), for the `provision()` function behind the command.
- The admin action **Provision database (create + migrate + activate)** on the client list does step 7 for selected clients.
