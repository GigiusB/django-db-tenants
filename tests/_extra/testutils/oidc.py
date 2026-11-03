"""Stand-ins for the per-tenant Authlib OIDC client, so SSO views run without an IdP."""

from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlencode

from django.http import HttpResponseRedirect

AUTHORIZE_URL = "https://idp.example.com/authorize"


@dataclass
class FakeOIDCClient:
    """Mimics the subset of ``authlib`` ``DjangoOAuth2App`` used by ``django_db_tenants.oidc.views``."""

    userinfo_claims: dict[str, Any] = field(default_factory=dict)
    id_token: str = "fake-id-token"
    metadata: dict[str, Any] = field(default_factory=dict)
    redirect_uris: list[str] = field(default_factory=list)

    def authorize_redirect(self, request: Any, redirect_uri: str) -> HttpResponseRedirect:
        self.redirect_uris.append(redirect_uri)
        return HttpResponseRedirect(f"{AUTHORIZE_URL}?{urlencode({'redirect_uri': redirect_uri})}")

    def authorize_access_token(self, request: Any) -> dict[str, Any]:
        return {"userinfo": self.userinfo_claims, "id_token": self.id_token}

    def userinfo(self, token: dict[str, Any]) -> dict[str, Any]:
        return self.userinfo_claims

    def load_server_metadata(self) -> dict[str, Any]:
        return self.metadata
