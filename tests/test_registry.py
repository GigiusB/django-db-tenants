from datetime import timedelta

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from freezegun import freeze_time

from django_db_tenants import registry
from django_db_tenants.exceptions import TenantInactive, TenantNotFound
from django_db_tenants.models import ClientDomain
from testutils.factories import ClientDomainFactory, ClientFactory

pytestmark = pytest.mark.django_db


def test_host_lookup_is_case_insensitive_and_cached():
    domain = ClientDomainFactory.create(domain="ACME.test")
    assert domain.domain == "acme.test"  # normalised on save

    assert registry.get_client_for_host("Acme.Test") == domain.client
    with CaptureQueriesContext(connection) as queries:
        registry.get_client_for_host("acme.test")
    assert len(queries) == 0


def test_unknown_host_miss_is_cached_for_ttl(settings):
    settings.DB_TENANTS = {**settings.DB_TENANTS, "CACHE_TTL": 60}
    with freeze_time("2026-01-01") as frozen:
        with pytest.raises(TenantNotFound):
            registry.get_client_for_host("late.test")

        # Created behind the cache's back (bulk_create skips post_save signals).
        client = ClientFactory.create(slug="late")
        ClientDomain.objects.bulk_create([ClientDomain(client=client, domain="late.test")])
        with pytest.raises(TenantNotFound):
            registry.get_client_for_host("late.test")

        frozen.tick(timedelta(seconds=61))
        assert registry.get_client_for_host("late.test") == client


def test_saving_a_domain_invalidates_negative_cache():
    with pytest.raises(TenantNotFound):
        registry.get_client_for_host("new.test")
    ClientDomainFactory.create(domain="new.test")
    assert registry.get_client_for_host("new.test").slug


@pytest.mark.parametrize("trait", ["suspended", "provisioning"])
def test_inactive_client_is_rejected(trait):
    ClientDomainFactory.create(domain="off.test", client=ClientFactory.create(**{trait: True}))
    with pytest.raises(TenantInactive):
        registry.get_client_for_host("off.test")


def test_saving_client_invalidates_cache():
    domain = ClientDomainFactory.create(domain="acme.test")
    registry.get_client_for_host("acme.test")
    client = domain.client
    client.status = client.Status.SUSPENDED
    client.save()
    with pytest.raises(TenantInactive):
        registry.get_client_for_host("acme.test")


def test_get_client_by_slug():
    client = ClientFactory.create(slug="acme")
    assert registry.get_client("acme") == client
    with pytest.raises(TenantNotFound):
        registry.get_client("missing")
