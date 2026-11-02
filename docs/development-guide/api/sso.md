# SSO

`django_db_tenants.sso` signs a tenant's users in through that tenant's own [OIDC](../../../glossary/#oidc) provider. The provider is configured on the `Client` row (`sso_enabled`, `oidc_*`), so adding one is a data change. The flow is drawn in [Architecture](../../architecture/#single-sign-on).

## Set up

```python
# urls.py
urlpatterns = [
    path("sso/", include("django_db_tenants.sso.urls")),
]
```

Register `https://<client-domain>/sso/callback/` as a redirect URI at each tenant's IdP.

## Views

URL names are in the `django_db_tenants` namespace.

| URL | Name | Methods | Behaviour |
|---|---|---|---|
| `login/` | `sso_login` | GET | Redirects to the IdP. A `?next=` URL on the same host is stored in the session |
| `callback/` | `sso_callback` | GET | Exchanges the code (Authlib validates state, nonce and the ID token signature), maps the claims to a user with `SSO_USER_SYNC`, logs them in with `SSO_AUTH_BACKEND`, stores the ID token in the session, redirects to `next` or `SSO_LOGIN_REDIRECT_URL` |
| `logout/` | `sso_logout` | GET, POST | Logs out locally, then redirects to the IdP's `end_session_endpoint` (with `id_token_hint` and `post_logout_redirect_uri`) when `SSO_RP_INITIATED_LOGOUT` is on and the IdP advertises one; otherwise to `SSO_LOGOUT_REDIRECT_URL` |

| Situation | Response |
|---|---|
| No tenant, or SSO disabled for it (login, callback) | 404 |
| IdP returned `?error=` to the callback | 400 with the error description |
| User sync returned `None` | 403 |

```html
<a href="{% url 'django_db_tenants:sso_login' %}?next={{ request.path|urlencode }}">Sign in with your company account</a>
```

## Map claims to users

`SSO_USER_SYNC` turns the IdP's claims into a user of the tenant database. The default, `default_user_sync`:

1. Refuses claims without `email`.
2. Finds the user by e-mail, case-insensitively.
3. Without a match, creates one when `client.oidc_auto_create_users` is on (username field set to the e-mail, unusable password), otherwise refuses.
4. Copies `given_name` and `family_name` into `first_name` and `last_name` when the model has them.
5. Refuses inactive users; saves and returns the others.

Replace it to restrict domains, map groups, or use another claim:

```python
# myproject/sso.py
from django_db_tenants.sso.sync import default_user_sync


def sync_user(client, userinfo, request):
    if not userinfo.get("email", "").endswith("@acme.com"):
        return None  # 403
    user = default_user_sync(client, userinfo, request)
    if user is not None and "admins" in userinfo.get("groups", []):
        user.is_staff = True
        user.save(update_fields=["is_staff"])
    return user
```

```python
DB_TENANTS = {"SSO_USER_SYNC": "myproject.sso.sync_user"}
```

The function runs with the tenant active, so its queries use the tenant database.

## Per-tenant OIDC clients

`get_oidc_client(client)` returns an Authlib remote app named `tenant_<slug>`, registered from the client's issuer, client id, secret and scopes, with discovery metadata cached in `CACHE_ALIAS`. It is registered again when the client's config version, issuer or client id changes. It raises `ValueError` when SSO is disabled for the client.

::: django_db_tenants.sso.oidc

::: django_db_tenants.sso.sync

::: django_db_tenants.sso.views
