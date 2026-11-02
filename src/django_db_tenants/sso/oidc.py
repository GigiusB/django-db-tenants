"""Per-tenant OpenID Connect clients built with Authlib.

Provider details come from the Client row, so onboarding a tenant's identity
provider is a data change, not a settings change.
"""

import threading

from authlib.integrations.django_client import OAuth
from django.core.cache import caches

from ..conf import app_settings

_lock = threading.Lock()
_oauth = None
_versions: dict[str, str] = {}


def _oauth_registry() -> OAuth:
    global _oauth
    if _oauth is None:
        with _lock:
            if _oauth is None:
                # Authlib caches discovery metadata in this cache.
                _oauth = OAuth(cache=caches[app_settings.CACHE_ALIAS])
    return _oauth


def get_oidc_client(client):
    """Return an Authlib remote app configured for this tenant's IdP."""
    if not client.sso_enabled:
        raise ValueError(f"SSO is not enabled for tenant {client.slug!r}")

    name = f"tenant_{client.slug}"
    version = f"{client.config_version()}|{client.oidc_issuer}|{client.oidc_client_id}"
    oauth = _oauth_registry()

    if _versions.get(name) != version:
        with _lock:
            if _versions.get(name) != version:
                # Drop a stale instance (credentials rotated) before re-registering.
                oauth._clients.pop(name, None)
                oauth.register(
                    name=name,
                    overwrite=True,
                    client_id=client.oidc_client_id,
                    client_secret=client.oidc_client_secret,
                    server_metadata_url=f"{client.oidc_issuer.rstrip('/')}/.well-known/openid-configuration",
                    client_kwargs={"scope": client.oidc_scopes},
                )
                _versions[name] = version
    return oauth.create_client(name)
