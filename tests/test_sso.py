import pytest
from django.contrib.auth import get_user_model

from django_db_tenants import tenant_context
from django_db_tenants.sso import views
from django_db_tenants.sso.oidc import get_oidc_client
from django_db_tenants.sso.sync import default_user_sync
from testutils.factories import ClientFactory, UserFactory
from testutils.sso import AUTHORIZE_URL, FakeOIDCClient

User = get_user_model()


@pytest.fixture
def sso_tenant(tenant_factory):
    return tenant_factory("acme", sso=True)


@pytest.fixture
def fake_oidc(monkeypatch):
    fake = FakeOIDCClient(userinfo_claims={"email": "Alice@Acme.test", "given_name": "Alice", "family_name": "A"})
    monkeypatch.setattr(views, "get_oidc_client", lambda client: fake)
    return fake


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
        tenant = tenant_factory(sso=True, oidc_auto_create_users=False)
        with tenant_context(tenant):
            assert default_user_sync(tenant, {"email": "dave@x.test"}) is None

    def test_denies_inactive_user(self, sso_tenant):
        with tenant_context(sso_tenant):
            UserFactory.create(email="eve@acme.test", is_active=False)
            assert default_user_sync(sso_tenant, {"email": "eve@acme.test"}) is None


# ------------------------------------------------------------------------------- views
def test_login_404_when_sso_disabled(client, acme):
    assert client.get("/sso/login/", HTTP_HOST="acme.test").status_code == 404


def test_login_redirects_to_idp(client, sso_tenant, fake_oidc):
    response = client.get("/sso/login/", {"next": "/notes/"}, HTTP_HOST="acme.test")
    assert response.status_code == 302
    assert response["Location"].startswith(AUTHORIZE_URL)
    assert fake_oidc.redirect_uris == ["http://acme.test/sso/callback/"]


def test_callback_logs_in_tenant_user(client, sso_tenant, fake_oidc):
    client.get("/sso/login/", {"next": "/notes/"}, HTTP_HOST="acme.test")
    response = client.get("/sso/callback/", HTTP_HOST="acme.test")

    assert response.status_code == 302
    assert response["Location"] == "/notes/"
    with tenant_context(sso_tenant):
        user = User.objects.get(email="alice@acme.test")
        assert client.session["_auth_user_id"] == str(user.pk)
        assert client.session[views.SESSION_ID_TOKEN] == "fake-id-token"


def test_callback_ignores_unsafe_next(client, sso_tenant, fake_oidc):
    client.get("/sso/login/", {"next": "https://evil.test/"}, HTTP_HOST="acme.test")
    assert client.get("/sso/callback/", HTTP_HOST="acme.test")["Location"] == "/"


def test_callback_idp_error(client, sso_tenant, fake_oidc):
    response = client.get("/sso/callback/", {"error": "access_denied"}, HTTP_HOST="acme.test")
    assert response.status_code == 400


def test_callback_denied_by_sync(client, sso_tenant, fake_oidc):
    fake_oidc.userinfo_claims = {}
    assert client.get("/sso/callback/", HTTP_HOST="acme.test").status_code == 403


def test_logout_redirects_to_end_session_endpoint(client, sso_tenant, fake_oidc):
    fake_oidc.metadata = {"end_session_endpoint": "https://idp.example.com/logout"}
    client.get("/sso/callback/", HTTP_HOST="acme.test")

    response = client.post("/sso/logout/", HTTP_HOST="acme.test")

    assert response["Location"].startswith("https://idp.example.com/logout?id_token_hint=fake-id-token")


def test_logout_without_sso_session(client, acme):
    response = client.post("/sso/logout/", HTTP_HOST="acme.test")
    assert response["Location"] == "http://acme.test/"


# ----------------------------------------------------------------------- authlib client
@pytest.mark.django_db
def test_get_oidc_client_requires_sso():
    with pytest.raises(ValueError, match="not enabled"):
        get_oidc_client(ClientFactory.create())


@pytest.mark.django_db
def test_get_oidc_client_reregisters_on_change():
    tenant = ClientFactory.create(sso=True, slug="acme")
    first = get_oidc_client(tenant)
    assert first.client_id == "acme-client"
    assert get_oidc_client(tenant) is first

    tenant.oidc_client_id = "rotated"
    second = get_oidc_client(tenant)
    assert second.client_id == "rotated"
