import pytest
from django.contrib.auth import get_user_model

from django_db_tenants import tenant_context
from django_db_tenants.models import Client
from django_db_tenants.router import TenantRouter
from testutils.factories import NoteFactory, UserFactory

User = get_user_model()


def test_tenant_data_is_isolated(acme, globex):
    with tenant_context(acme):
        UserFactory.create(username="alice")
        assert User.objects.count() == 1
    with tenant_context(globex):
        assert User.objects.count() == 0
    assert User.objects.count() == 0  # shared database


def test_shared_app_always_uses_default(acme, globex):
    with tenant_context(acme):
        assert Client.objects.count() == 2
        assert Client.objects.db == "default"


def test_relations_stay_in_tenant_db(acme):
    with tenant_context(acme):
        note = NoteFactory.create()
        assert note._state.db == "acme"
        assert note.author._state.db == "acme"


def test_allow_relation_rejects_cross_database(acme, globex):
    with tenant_context(acme):
        alice = UserFactory.create()
    with tenant_context(globex):
        bob = UserFactory.create()
    assert TenantRouter().allow_relation(alice, bob) is False
    assert TenantRouter().allow_relation(alice, alice) is None


@pytest.mark.parametrize(
    ("db", "app_label", "expected"),
    [
        ("default", "django_db_tenants", True),
        ("acme", "django_db_tenants", False),
        ("default", "auth", True),  # TENANT_APPS_ON_DEFAULT
        ("acme", "auth", True),
        ("acme", "notes", True),
    ],
)
def test_allow_migrate(db, app_label, expected):
    assert TenantRouter().allow_migrate(db, app_label) is expected


def test_allow_migrate_without_tenant_apps_on_default(settings):
    settings.DB_TENANTS = {**settings.DB_TENANTS, "TENANT_APPS_ON_DEFAULT": False}
    assert TenantRouter().allow_migrate("default", "auth") is False
