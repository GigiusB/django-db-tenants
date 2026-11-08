import pytest
from django.http import HttpResponse

from django_db_tenants import tenant_context
from testutils.factories import UserFactory


def test_routes_each_host_to_its_database(client, acme, globex):
    with tenant_context(acme):
        UserFactory.create()

    assert client.get("/whoami/", HTTP_HOST="acme.test").json() == {"tenant": "acme", "users": 1}
    assert client.get("/whoami/", HTTP_HOST="globex.test").json() == {"tenant": "globex", "users": 0}


def test_host_port_is_ignored(client, acme):
    assert client.get("/whoami/", HTTP_HOST="acme.test:8000").json()["tenant"] == "acme"


@pytest.mark.django_db
def test_control_host_uses_shared_db(client):
    assert client.get("/whoami/", HTTP_HOST="control.test").json() == {"tenant": None, "users": 0}


@pytest.mark.django_db
def test_unknown_host_is_404(client):
    assert client.get("/whoami/", HTTP_HOST="nobody.test").status_code == 404


def test_suspended_tenant_is_404(client, tenant_factory):
    tenant_factory("gone", suspended=True)
    assert client.get("/whoami/", HTTP_HOST="gone.test").status_code == 404


@pytest.mark.django_db
def test_exempt_paths_skip_resolution(client):
    response = client.get("/healthz", HTTP_HOST="nobody.test")
    assert response.status_code == 200
    assert response.content == b"ok"


def custom_not_found(request, exc):
    return HttpResponse(f"no tenant: {exc}", status=410)


@pytest.mark.django_db
def test_custom_not_found_handler(client, settings):
    settings.DB_TENANTS = {**settings.DB_TENANTS, "NOT_FOUND_HANDLER": f"{__name__}.custom_not_found"}
    response = client.get("/whoami/", HTTP_HOST="nobody.test")
    assert response.status_code == 410
    assert response.content == b"no tenant: nobody.test"


def test_header_resolver(client, settings, acme):
    settings.DB_TENANTS = {**settings.DB_TENANTS, "RESOLVER": "django_db_tenants.resolvers.resolve_by_header"}
    assert client.get("/whoami/", HTTP_X_TENANT="acme").json()["tenant"] == "acme"
    assert client.get("/whoami/").json()["tenant"] is None
    assert client.get("/whoami/", HTTP_X_TENANT="nope").status_code == 404


@pytest.mark.django_db
def test_unknown_host_stays_404_when_served_from_cache(client):
    # Regression: the cached "miss" sentinel was compared by identity, which a
    # pickling cache backend does not preserve, so the second request was a 500.
    assert client.get("/whoami/", HTTP_HOST="nobody.test").status_code == 404
    assert client.get("/whoami/", HTTP_HOST="nobody.test").status_code == 404
