# Router

`TenantRouter` sends the models of [shared apps](../../glossary.md#shared-apps) to the shared database and every other model to the active tenant's database.

```python
DATABASE_ROUTERS = ["django_db_tenants.router.TenantRouter"]
```

## Decisions

| Method | Shared app | Other app |
|---|---|---|
| `db_for_read`, `db_for_write` | `TEMPLATE_ALIAS` | active tenant alias, else `TEMPLATE_ALIAS` |
| `allow_migrate(db, ...)` | only on `TEMPLATE_ALIAS` | on tenant aliases; on `TEMPLATE_ALIAS` when `TENANT_APPS_ON_DEFAULT` |
| `allow_relation(obj1, obj2)` | `False` when both objects are saved in different databases, otherwise `None` (no opinion) | same |

Add other routers after this one only for aliases it does not know about: Django uses the first router that returns a non-`None` answer, and `TenantRouter` always answers `db_for_read`, `db_for_write` and `allow_migrate`.

See [Architecture](../architecture.md#database-routing) for the consequences on foreign keys.

::: django_db_tenants.router
