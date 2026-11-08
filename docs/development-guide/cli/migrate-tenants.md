# migrate_tenants

Run migrations on tenant databases: by default on every `active` client, one after the other. Run it after `migrate` on the shared database.

Source: `src/django_db_tenants/management/commands/migrate_tenants.py`.

## Synopsis

```text
python manage.py migrate_tenants [--slug SLUG ...] [--include-inactive] [--fake]
```

## Options

| Option | Type | Default | Effect |
|---|---|---|---|
| `--slug` | string, repeatable | none | Migrate only these clients. Their status is **not** checked, so suspended and provisioning clients named here are migrated too. Unknown slugs are ignored |
| `--include-inactive` | flag | off | Migrate every client, whatever its status. Ignored when `--slug` is given |
| `--fake` | flag | off | Passed to `migrate`: mark migrations as applied without running them |
| `--verbosity` | `0`-`3` | `1` | Passed to `migrate` for each tenant |

Each tenant runs `migrate --database=<slug> --no-input`, so the [router](../api/router.md) applies only the tenant apps' migrations.

## Output and exit status

```text
==> acme
Operations to perform: ...
==> globex
    failed: <error message>
```

| Outcome | Last line | Exit status |
|---|---|---|
| Every tenant migrated | `All tenants migrated.` | `0` |
| At least one tenant failed | none (errors are printed per tenant, the others still run) | `1` |

A failure on one tenant does not stop the others; deployment scripts can rely on the exit status.

## Examples

```bash
python manage.py migrate && python manage.py migrate_tenants   # deployment
python manage.py migrate_tenants --slug acme --slug globex      # two tenants
python manage.py migrate_tenants --include-inactive             # suspended ones too
python manage.py migrate_tenants --slug acme --fake             # mark as applied
```

## See also

- [`migrate_tenant()`](../api/provisioning.md), which the command calls per client.
- [`for_each_tenant()`](../api/tasks.md), to write similar commands of your own.
