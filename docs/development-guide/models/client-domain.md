# ClientDomain

`django_db_tenants.models.ClientDomain`: a host name that belongs to a [Client](../client/). Table `django_db_tenants_clientdomain`, in the [shared database](../../../glossary/#shared-database) only.

`resolve_by_host`, the default [resolver](../../../glossary/#resolver), looks the request's host up in this table. A client can have any number of domains.

## Relations

| Field | Target | On delete | Reverse accessor |
|---|---|---|---|
| `client` (required) | [Client](../client/) | `CASCADE` | `client.domains` |

## Fields

| Field | Type | Required | Default | Meaning |
|---|---|---|---|---|
| `domain` | `CharField(253)`, unique | yes | | Host name without port. Lower-cased and stripped on `save()` |
| `is_primary` | `BooleanField` | yes | `False` | Marks the client's main domain. Informational: resolution ignores it. `provision_tenant` sets it on the first `--domain` |

Default ordering: primary domains first, then `domain`. `str(domain)` is the host name.

## Side effects of saving and deleting

Saving or deleting a domain deletes the registry cache entry of that host and every cache entry of its client, so a new domain resolves at once in processes that share the cache. Renaming a domain leaves the old host's entry cached until `CACHE_TTL` expires; see [Architecture](../../architecture/#client-lookup-cache-and-invalidation).

## Example

```python
from django_db_tenants.models import Client, ClientDomain

acme = Client.objects.using("default").get(slug="acme")
ClientDomain.objects.using("default").create(client=acme, domain="ACME.example.org")
# stored as "acme.example.org"; https://acme.example.org/ now serves ACME
```

## Next steps

See the commands that manage clients and domains in the [CLI reference](../../cli/).
