"""Per-tenant OpenID Connect clients built with Authlib.

Provider details come from the client's :class:`OidcStrategy` (``Client.db_params["SSO"]``),
so onboarding a tenant's identity provider is a data change, not a settings change.
"""

import threading

from authlib.integrations.django_client import OAuth
from django.core.cache import caches

from ..conf import app_settings
from .strategy import get_oidc_config

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
    config = get_oidc_config(client)
    if config is None:
        raise ValueError(f"Tenant {client.slug!r} does not use an OidcStrategy")

    name = f"tenant_{client.slug}"
    version = f"{client.config_version()}|{config.issuer}|{config.client_id}"
    oauth = _oauth_registry()

    if _versions.get(name) != version:
        with _lock:
            if _versions.get(name) != version:
                # Drop a stale instance (credentials rotated) before re-registering.
                oauth._clients.pop(name, None)
                oauth.register(
                    name=name,
                    overwrite=True,
                    client_id=config.client_id,
                    client_secret=config.client_secret,
                    server_metadata_url=config.server_metadata_url,
                    client_kwargs={"scope": config.scopes},
                )
                _versions[name] = version
    return oauth.create_client(name)
