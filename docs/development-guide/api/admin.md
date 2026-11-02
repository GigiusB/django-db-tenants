# Admin

`django_db_tenants.admin` registers `Client` in the Django admin, with its domains inline. Use it on a [control host](../../../glossary/#control-host): `Client` lives in the shared database.

## Client admin

| Feature | Detail |
|---|---|
| List columns | name, slug, status, database strategy, database name, SSO enabled, last update |
| Filters | status, database strategy, SSO enabled |
| Search | name, slug, domain |
| Sections | general (name, slug, status), **Database** (strategy select, database name, `db_params` as JSON), **Single sign-on**, **Timestamps** (collapsed, read-only) |
| Slug | editable on creation, read-only afterwards |
| Secrets | `oidc_client_secret` uses a password input that renders the stored value, so saving the form keeps it; `db_params` is shown decrypted in a JSON text area |
| Domains | `ClientDomain` tabular inline, one empty row |
| Action | **Provision database (create + migrate + activate)**: runs `provision()` for each selected client and reports success or the error per client |

!!! note "Secrets in the page source"
    The change form contains the decrypted `db_params` (including database passwords) and OIDC client secret in its HTML. Give the `change_client` permission only to people allowed to see tenant credentials.

The form validates with `Client.clean()`, so reserved slugs, SSO without issuer or client id, and `db_params` the strategy refuses are rejected. The strategy select lists the registered strategies only.

::: django_db_tenants.admin
