"""The OpenID Connect database strategy: the connection of :class:`TemplateOverlay`, plus
the client's OpenID Connect provider, read from ``Client.db_params["SSO"]``.

This module needs no extra dependency; the login views (``django_db_tenants.oidc.urls``)
need Authlib: ``pip install django-db-tenants[oidc]``.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator

from ..strategies import TemplateOverlay

if TYPE_CHECKING:
    from ..models import Client


@dataclass(frozen=True)
class OidcConfig:
    """A client's OpenID Connect provider, as returned by :meth:`OidcStrategy.oidc_config`."""

    issuer: str
    client_id: str
    client_secret: str = ""
    scopes: str = "openid email profile"
    #: The default user sync creates a local user on first SSO login.
    auto_create_users: bool = True

    def __repr__(self) -> str:  # keep the secret out of logs and tracebacks
        return f"OidcConfig(issuer={self.issuer!r}, client_id={self.client_id!r})"

    @property
    def server_metadata_url(self) -> str:
        return f"{self.issuer.rstrip('/')}/.well-known/openid-configuration"


class OidcStrategy(TemplateOverlay):
    """:class:`TemplateOverlay` whose users sign in through the client's OpenID Connect provider.

    The connection is built as by :class:`TemplateOverlay`, from the ``DATABASES`` keys in
    ``db_params`` (``ENGINE``, ``HOST``, ``USER``, ``PASSWORD``, ``OPTIONS``, ...) with
    ``NAME = client.db_name``. The provider is the ``db_params["SSO"]`` object: ``ISSUER``
    and ``CLIENT_ID`` (required), ``CLIENT_SECRET``, ``SCOPES``, ``AUTO_CREATE_USERS``.
    Missing, empty and ``null`` optional values take the :class:`OidcConfig` defaults.

    Not registered by default: add ``"django_db_tenants.oidc.OidcStrategy"`` to
    ``DB_TENANTS["DATABASE_STRATEGIES"]`` and mount ``django_db_tenants.oidc.urls``.
    """

    label = "Template connection + overrides, OIDC single sign-on"
    sso_key = "SSO"
    #: Keys accepted in ``db_params["SSO"]``, mapped to the :class:`OidcConfig` field they set.
    sso_keys: ClassVar[dict[str, str]] = {
        "ISSUER": "issuer",
        "CLIENT_ID": "client_id",
        "CLIENT_SECRET": "client_secret",
        "SCOPES": "scopes",
        "AUTO_CREATE_USERS": "auto_create_users",
    }
    param_keys = TemplateOverlay.settings_keys | {"MAINTENANCE_DB", sso_key}

    def validate(self) -> None:
        super().validate()
        sso = self.params.get(self.sso_key)
        if not isinstance(sso, dict):
            raise ValidationError({"db_params": f"{self} requires an SSO object."})
        unknown = sorted(set(sso) - set(self.sso_keys))
        if unknown:
            raise ValidationError(
                {
                    "db_params": f"SSO does not accept {', '.join(unknown)}. "
                    f"Allowed keys: {', '.join(sorted(self.sso_keys))}."
                }
            )
        for key in ("ISSUER", "CLIENT_ID", "CLIENT_SECRET", "SCOPES"):
            if not isinstance(sso.get(key) or "", str):
                raise ValidationError({"db_params": f"SSO {key} must be a string."})
        if not isinstance(sso.get("AUTO_CREATE_USERS", True), bool):
            raise ValidationError({"db_params": "SSO AUTO_CREATE_USERS must be true or false."})
        if not (sso.get("ISSUER") and sso.get("CLIENT_ID")):
            raise ValidationError({"db_params": "SSO requires an OIDC ISSUER and CLIENT_ID."})
        try:
            URLValidator(schemes=["http", "https"])(sso["ISSUER"])
        except ValidationError:
            raise ValidationError({"db_params": "SSO ISSUER must be an http(s) URL."}) from None

    def oidc_config(self) -> OidcConfig | None:
        """The client's provider; ``None`` while ``db_params["SSO"]`` lacks ``ISSUER`` or ``CLIENT_ID``."""
        sso = self.params.get(self.sso_key)
        if not isinstance(sso, dict) or not (sso.get("ISSUER") and sso.get("CLIENT_ID")):
            return None  # rejected by validate()
        return OidcConfig(**{field: sso[key] for key, field in self.sso_keys.items() if sso.get(key) not in (None, "")})


def get_oidc_config(client: "Client") -> OidcConfig | None:
    """The client's provider when it uses an :class:`OidcStrategy`; ``None`` for any other strategy."""
    strategy = client.db_strategy
    return strategy.oidc_config() if isinstance(strategy, OidcStrategy) else None
