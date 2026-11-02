from django.contrib.auth import get_user_model

from django_db_tenants import get_current_tenant_alias, tenant_context
from django_db_tenants.tasks import for_each_tenant, with_tenant
from testutils.factories import UserFactory

User = get_user_model()


@with_tenant
def count_users(tenant):
    return get_current_tenant_alias(), User.objects.count()


def test_with_tenant_positional_and_keyword(acme, globex):
    with tenant_context(acme):
        UserFactory.create_batch(2)
    assert count_users("acme") == ("acme", 2)
    assert count_users(tenant=globex) == ("globex", 0)
    assert get_current_tenant_alias() is None


def test_for_each_tenant_skips_inactive(acme, globex, tenant_factory):
    tenant_factory("off", suspended=True)
    with tenant_context(globex):
        UserFactory.create()

    assert for_each_tenant(lambda c: User.objects.count()) == {"acme": 0, "globex": 1}
    assert set(for_each_tenant(lambda c: None, only_active=False)) == {"acme", "globex", "off"}
