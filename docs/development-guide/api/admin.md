# Admin

`django_db_tenants.admin` registers `Client` in the Django admin, with its domains inline. Use it on a [control host](../../glossary.md#control-host): `Client` lives in the shared database.

## Client admin

| Feature | Detail |
|---|---|
| List columns | name, slug, status, database strategy, database name, last update |
| Filters | status, database strategy |
| Search | name, slug, domain |
| Sections | general (name, slug, status), **Database** (strategy select, database name, `db_params` as JSON), **Timestamps** (collapsed, read-only) |
| Slug | editable on creation, read-only afterwards |
| Secrets | `db_params`, with the database password and any other secret the strategy keeps there, is shown decrypted in a JSON text area |
| Domains | `ClientDomain` tabular inline, one empty row |
| Action | **Provision database (create + migrate + activate)**: runs `provision()` for each selected client and reports success or the error per client |

!!! note "Secrets in the page source"
    The change form contains the decrypted `db_params` (including database passwords) in its HTML. Give the `change_client` permission only to people allowed to see tenant credentials.

The form validates with `Client.clean()`, so reserved slugs and `db_params` the strategy refuses are rejected. The strategy select lists the registered strategies only.

::: django_db_tenants.admin
