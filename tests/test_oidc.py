from collections.abc import Callable

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command

from django_db_tenants import tenant_context
from django_db_tenants.models import Client
from django_db_tenants.oidc import OidcConfig, OidcStrategy, get_oidc_config, views
from django_db_tenants.oidc.client import get_oidc_client
from django_db_tenants.oidc.sync import default_user_sync
from django_db_tenants.strategies import template_settings
from testutils.factories import OIDC_STRATEGY, ClientFactory, UserFactory, sso_params
from testutils.oidc import AUTHORIZE_URL, FakeOIDCClient

User = get_user_model()

pytestmark = pytest.mark.django_db


@pytest.fixture
def sso_tenant(tenant_factory):
    return tenant_factory("acme", sso=True)


@pytest.fixture
def fake_oidc(monkeypatch):
    fake = FakeOIDCClient(userinfo_claims={"email": "Alice@Acme.test", "given_name": "Alice", "family_name": "A"})
    monkeypatch.setattr(views, "get_oidc_client", lambda client: fake)
    return fake


# ---------------------------------------------------------------------------- strategy
def test_only_oidc_strategy_clients_have_a_provider():
    params = {"HOST": "db2", **sso_params("acme")}
    overlay = ClientFactory.build(db_params=params)
    assert get_oidc_config(overlay) is None  # TemplateOverlay knows nothing of OIDC
    with pytest.raises(ValidationError, match="does not accept SSO"):
        overlay.clean()

    client = ClientFactory.build(db_strategy=OIDC_STRATEGY, db_params=params)
    client.clean()
    assert isinstance(client.db_strategy, OidcStrategy)
    assert get_oidc_config(client) == client.db_strategy.oidc_config()
    assert client.db_strategy.oidc_config().client_id == "acme-client"


def test_oidc_strategy_requires_issuer_and_client_id():
    with pytest.raises(ValidationError, match="SSO requires"):
        ClientFactory.build(sso=True, db_params={"SSO": {"CLIENT_ID": "x"}}).full_clean()
    ClientFactory.build(sso=True).full_clean()


@pytest.mark.parametrize(
    ("params", "message"),
    [
        ({}, "requires an SSO object"),
        ({"SSO": "on"}, "requires an SSO object"),
        ({"SSO": {"ISSUER": "https://idp.test", "CLIENT_ID": "x", "ENABLED": True}}, "SSO does not accept ENABLED"),
        ({"SSO": {"ISSUER": "idp.test", "CLIENT_ID": "x"}}, "ISSUER must be an http"),
        ({"SSO": {"ISSUER": "https://idp.test", "CLIENT_ID": 42}}, "CLIENT_ID must be a string"),
        (
            {"SSO": {"ISSUER": "https://idp.test", "CLIENT_ID": "x", "AUTO_CREATE_USERS": "yes"}},
            "AUTO_CREATE_USERS must be true or false",
        ),
        ({"NAME": "x", **sso_params("acme")}, "does not accept NAME"),  # TemplateOverlay's checks still apply
    ],
)
def test_oidc_strategy_params_are_validated(params, message):
    with pytest.raises(ValidationError, match=message):
        ClientFactory.build(sso=True, db_params=params).full_clean()


def test_oidc_config_is_read_from_db_params():
    client = ClientFactory.build(sso=True, db_params=sso_params("acme", SCOPES="", AUTO_CREATE_USERS=False))
    config = client.db_strategy.oidc_config()
    assert config == OidcConfig(
        issuer="https://idp.example.com/acme",
        client_id="acme-client",
        client_secret="oidc-secret",
        scopes="openid email profile",  # empty values fall back to the defaults
        auto_create_users=False,
    )
    assert config.server_metadata_url == "https://idp.example.com/acme/.well-known/openid-configuration"
    assert "oidc-secret" not in repr(config)


def test_oidc_strategy_builds_the_connection_like_template_overlay():
    client = ClientFactory.build(
        slug="oidc",
        sso=True,
        db_params={"USER": "acme", "PASSWORD": "pw", "OPTIONS": {"connect_timeout": 3}, **sso_params("oidc")},
    )
    cfg = client.db_strategy.connection_settings(template_settings())
    assert (cfg["NAME"], cfg["USER"], cfg["PASSWORD"]) == (client.db_name, "acme", "pw")
    assert cfg["OPTIONS"]["connect_timeout"] == 3
    assert "SSO" not in cfg


def test_provision_tenant_with_oidc_strategy(tenant_db_name: Callable[[str], str]):
    call_command(
        "provision_tenant",
        "cmd",
        name="Via Command",
        db_name=tenant_db_name("cmd"),
        db_strategy=OIDC_STRATEGY,
        db_params='{"SSO": {"ISSUER": "https://idp.example.com", "CLIENT_ID": "abc"}}',
        skip_create_db=True,
        skip_migrate=True,
        verbosity=0,
    )
    assert get_oidc_config(Client.objects.get(slug="cmd")) == OidcConfig("https://idp.example.com", "abc")


# --------------------------------------------------------------------------- user sync
class TestDefaultUserSync:
    def test_creates_user_in_tenant_db(self, sso_tenant):
        with tenant_context(sso_tenant):
            user = default_user_sync(sso_tenant, {"email": " Bob@Acme.test ", "given_name": "Bob"})
            assert user is not None
            assert (user.username, user.email, user.first_name) == ("bob@acme.test", "bob@acme.test", "Bob")
            assert not user.has_usable_password()
        assert not User.objects.exists()  # nothing in the shared DB

    def test_matches_existing_user_by_email(self, sso_tenant):
        with tenant_context(sso_tenant):
            existing = UserFactory.create(email="carol@acme.test")
            assert default_user_sync(sso_tenant, {"email": "CAROL@acme.test"}) == existing

    def test_denies_without_email(self, sso_tenant):
        with tenant_context(sso_tenant):
            assert default_user_sync(sso_tenant, {}) is None

    def test_denies_unknown_user_when_auto_create_disabled(self, tenant_factory):
        tenant = tenant_factory("dave", sso=True, db_params=sso_params("dave", AUTO_CREATE_USERS=False))
        with tenant_context(tenant):
            assert default_user_sync(tenant, {"email": "dave@x.test"}) is None

    def test_denies_inactive_user(self, sso_tenant):
        with tenant_context(sso_tenant):
            UserFactory.create(email="eve@acme.test", is_active=False)
            assert default_user_sync(sso_tenant, {"email": "eve@acme.test"}) is None


# ------------------------------------------------------------------------------- views
def test_login_404_without_oidc_strategy(client, acme):
    assert client.get("/oidc/login/", HTTP_HOST="acme.test").status_code == 404


def test_login_redirects_to_idp(client, sso_tenant, fake_oidc):
    response = client.get("/oidc/login/", {"next": "/notes/"}, HTTP_HOST="acme.test")
    assert response.status_code == 302
    assert response["Location"].startswith(AUTHORIZE_URL)
    assert fake_oidc.redirect_uris == ["http://acme.test/oidc/callback/"]


def test_callback_logs_in_tenant_user(client, sso_tenant, fake_oidc):
    client.get("/oidc/login/", {"next": "/notes/"}, HTTP_HOST="acme.test")
    response = client.get("/oidc/callback/", HTTP_HOST="acme.test")

    assert response.status_code == 302
    assert response["Location"] == "/notes/"
    with tenant_context(sso_tenant):
        user = User.objects.get(email="alice@acme.test")
        assert client.session["_auth_user_id"] == str(user.pk)
        assert client.session[views.SESSION_ID_TOKEN] == "fake-id-token"


def test_settings_come_from_the_oidc_section_of_db_tenants(client, sso_tenant, fake_oidc, settings):
    settings.DB_TENANTS = {**settings.DB_TENANTS, "OIDC": {"LOGIN_REDIRECT_URL": "/notes/"}}
    assert client.get("/oidc/callback/", HTTP_HOST="acme.test")["Location"] == "/notes/"


def test_callback_ignores_unsafe_next(client, sso_tenant, fake_oidc):
    client.get("/oidc/login/", {"next": "https://evil.test/"}, HTTP_HOST="acme.test")
    assert client.get("/oidc/callback/", HTTP_HOST="acme.test")["Location"] == "/"


def test_callback_idp_error(client, sso_tenant, fake_oidc):
    response = client.get("/oidc/callback/", {"error": "access_denied"}, HTTP_HOST="acme.test")
    assert response.status_code == 400


def test_callback_denied_by_sync(client, sso_tenant, fake_oidc):
    fake_oidc.userinfo_claims = {}
    assert client.get("/oidc/callback/", HTTP_HOST="acme.test").status_code == 403


def test_logout_redirects_to_end_session_endpoint(client, sso_tenant, fake_oidc):
    fake_oidc.metadata = {"end_session_endpoint": "https://idp.example.com/logout"}
    client.get("/oidc/callback/", HTTP_HOST="acme.test")

    response = client.post("/oidc/logout/", HTTP_HOST="acme.test")

    assert response["Location"].startswith("https://idp.example.com/logout?id_token_hint=fake-id-token")


def test_logout_without_sso_session(client, acme):
    response = client.post("/oidc/logout/", HTTP_HOST="acme.test")
    assert response["Location"] == "http://acme.test/"


# ----------------------------------------------------------------------- authlib client
def test_get_oidc_client_requires_oidc_strategy():
    with pytest.raises(ValueError, match="does not use an OidcStrategy"):
        get_oidc_client(ClientFactory.create(db_params=sso_params("off")))


def test_get_oidc_client_reregisters_on_change():
    tenant = ClientFactory.create(sso=True, slug="acme")
    first = get_oidc_client(tenant)
    assert first.client_id == "acme-client"
    assert first.client_kwargs["scope"] == "openid email profile"
    assert get_oidc_client(tenant) is first

    tenant.db_params["SSO"]["CLIENT_ID"] = "rotated"
    second = get_oidc_client(tenant)
    assert second.client_id == "rotated"
