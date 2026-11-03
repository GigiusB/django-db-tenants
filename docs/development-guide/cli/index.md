# CLI reference

Who is this for: developers and operators who onboard tenants, migrate their databases or inspect them from a shell.

The library adds three Django management commands. Run them like any other command, with the project's settings:

```bash
python manage.py <command> [options]
```

| Command | Purpose | Page |
|---|---|---|
| `provision_tenant` | Create or update a client and its domains, create its database, migrate it, activate it | [provision_tenant](provision-tenant.md) |
| `migrate_tenants` | Run migrations on every tenant database, or on chosen ones | [migrate_tenants](migrate-tenants.md) |
| `tenant_shell` | Open a Django shell with a tenant active | [tenant_shell](tenant-shell.md) |

All three also accept Django's standard options (`--settings`, `--pythonpath`, `--verbosity`, `--traceback`, `--no-color`, `--force-color`, `--skip-checks`).

Plain `migrate` still manages the [shared database](../../glossary.md#shared-database): run it first on every deployment, then `migrate_tenants`.

```bash
python manage.py migrate            # shared database
python manage.py migrate_tenants    # every active tenant database
```

## Next steps

Onboard a first tenant with [provision_tenant](provision-tenant.md).
