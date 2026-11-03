"""Per-tenant OpenID Connect single sign-on, for clients whose database strategy is
:class:`OidcStrategy`. Optional: the rest of the library does not depend on it.

Set up::

    DB_TENANTS = {"DATABASE_STRATEGIES": ["django_db_tenants.oidc.OidcStrategy"]}
    urlpatterns = [path("oidc/", include("django_db_tenants.oidc.urls"))]
"""

from .strategy import OidcConfig, OidcStrategy, get_oidc_config

__all__ = ["OidcConfig", "OidcStrategy", "get_oidc_config"]
