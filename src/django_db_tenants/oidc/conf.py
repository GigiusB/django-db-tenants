"""Settings of the OpenID Connect login, in the ``OIDC`` sub-dict of ``DB_TENANTS``::

DB_TENANTS = {
    "OIDC": {
        "USER_SYNC": "myproject.sso.sync_user",
        "LOGIN_REDIRECT_URL": "/notes/",
    },
}
"""

from ..conf import AppSettings

DEFAULTS = {
    # Dotted path of a callable(client, userinfo, request) -> user | None (None refuses the login).
    "USER_SYNC": "django_db_tenants.oidc.sync.default_user_sync",
    # Backend recorded in the session by auth.login() after the callback.
    "AUTH_BACKEND": "django.contrib.auth.backends.ModelBackend",
    "LOGIN_REDIRECT_URL": "/",
    "LOGOUT_REDIRECT_URL": "/",
    # On logout, redirect to the provider's end_session_endpoint when it advertises one.
    "RP_INITIATED_LOGOUT": True,
}

oidc_settings = AppSettings(DEFAULTS, frozenset({"USER_SYNC"}), section="OIDC")
