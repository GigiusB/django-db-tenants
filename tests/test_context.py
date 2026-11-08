import pytest

from django_db_tenants import get_current_tenant, get_current_tenant_alias, tenant_context
from django_db_tenants.db import is_registered
from django_db_tenants.exceptions import TenantNotFound


def test_no_tenant_by_default():
    assert get_current_tenant() is None
    assert get_current_tenant_alias() is None


def test_accepts_slug_and_registers_alias(acme):
    with tenant_context("acme") as client:
        assert client.pk == acme.pk
        assert get_current_tenant_alias() == "acme"
        assert is_registered("acme")
    assert get_current_tenant() is None


def test_accepts_client_instance(acme):
    with tenant_context(acme):
        assert get_current_tenant() == acme


def test_nesting_restores_outer_tenant(acme, globex):
    with tenant_context(acme):
        with tenant_context(globex):
            assert get_current_tenant_alias() == "globex"
        with tenant_context(None):
            assert get_current_tenant_alias() is None
        assert get_current_tenant_alias() == "acme"


def test_resets_on_exception(acme):
    with pytest.raises(RuntimeError), tenant_context(acme):
        raise RuntimeError
    assert get_current_tenant() is None


@pytest.mark.django_db
def test_unknown_slug():
    with pytest.raises(TenantNotFound), tenant_context("nope"):
        pass
