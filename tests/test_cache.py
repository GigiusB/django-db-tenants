import pytest
from django.core.cache import cache

from django_db_tenants import registry, tenant_context
from django_db_tenants.cache import tenant_key_func
from django_db_tenants.exceptions import TenantInactive
from testutils.factories import ClientDomainFactory


@pytest.mark.parametrize(
    ("tenant", "key", "expected"),
    [
        (None, "stats", "p:1:stats"),  # Django's default format: shared keys don't move
        ("acme", "stats", "p:1:@acme:stats"),
        (
            "acme",
            "django_db_tenants:host:acme.test",
            "p:1:django_db_tenants:host:acme.test",
        ),  # library keys stay shared
    ],
)
def test_key_format(acme, tenant, key, expected):
    with tenant_context(tenant):
        assert tenant_key_func(key, "p", 1) == expected


def test_tenants_do_not_see_each_others_keys(acme, globex):
    cache.set("stats", "shared")
    with tenant_context(acme):
        cache.set("stats", "acme")
    with tenant_context(globex):
        assert cache.get("stats") is None
        cache.set("stats", "globex")

    assert cache.get("stats") == "shared"
    with tenant_context(acme):
        assert cache.get("stats") == "acme"
        cache.delete("stats")
    with tenant_context(globex):
        assert cache.get("stats") == "globex"


def test_cache_session_backend_is_per_tenant(client, settings, acme, globex):
    settings.SESSION_ENGINE = "django.contrib.sessions.backends.cache"
    with tenant_context(acme):
        session = client.session
        session["who"] = "acme"
        session.save()
        key = session.session_key
    with tenant_context(globex):
        assert not cache.has_key(f"django.contrib.sessions.cache{key}")
    with tenant_context(acme):
        assert cache.get(f"django.contrib.sessions.cache{key}") == {"who": "acme"}


def test_registry_cache_is_shared_across_tenant_contexts(acme, globex):
    # Lookups and invalidations of the Client registry happen from whatever tenant
    # is active; they must all hit the same keys or invalidation would miss.
    ClientDomainFactory.create(client=acme, domain="alias.test", is_primary=False)
    with tenant_context(globex):
        assert registry.get_client_for_host("alias.test") == acme  # cached while globex is active

    acme.status = acme.Status.SUSPENDED
    acme.save()  # post_save invalidates with no tenant active

    with tenant_context(globex), pytest.raises(TenantInactive):
        registry.get_client_for_host("alias.test")
