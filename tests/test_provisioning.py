"""These tests run real migrations, so they are slower than the rest."""

from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace

import pytest
from django.core.management import CommandError, call_command
from django.db import connections

from django_db_tenants import provisioning, tenant_context
from django_db_tenants.db import is_registered
from django_db_tenants.models import Client, ClientDomain
from django_db_tenants.provisioning import create_database, drop_database, provision
from django_db_tenants.strategies import TemplateOverlay
from testutils.databases import selected_backend
from testutils.factories import ClientFactory

pytestmark = pytest.mark.django_db


def test_provision_creates_migrates_and_activates(tenant_db_name: Callable[[str], str]):
    client = ClientFactory.create(provisioning=True, slug="fresh", db_name=tenant_db_name("fresh"))

    provision(client)

    client.refresh_from_db()
    assert client.status == Client.Status.ACTIVE
    tables = connections["fresh"].introspection.table_names()
    assert "auth_user" in tables
    assert "notes_note" in tables
    assert "django_db_tenants_client" not in tables  # shared app stays in the shared DB


@pytest.mark.parametrize("operation", ["create_database", "drop_database"])
def test_unsupported_vendor(monkeypatch, operation):
    monkeypatch.setattr(
        TemplateOverlay,
        "_server",
        lambda self, **changes: SimpleNamespace(vendor="oracle", settings_dict={"NAME": "x"}),
    )
    with pytest.raises(NotImplementedError, match="oracle"):
        getattr(provisioning, operation)(ClientFactory.build())


def test_drop_database(tenant_db_name: Callable[[str], str]):
    client = ClientFactory.create(provisioning=True, slug="doomed", db_name=tenant_db_name("doomed"))
    provision(client)
    assert "auth_user" in connections["doomed"].introspection.table_names()

    drop_database(client)

    assert not is_registered("doomed")
    if selected_backend() == "sqlite":
        assert not Path(client.db_name).exists()
    else:  # the name is free again: creating it without IF NOT EXISTS succeeds
        assert create_database(client, if_not_exists=False)
    drop_database(client)  # idempotent


def test_provision_tenant_command(tenant_db_name: Callable[[str], str]):
    call_command(
        "provision_tenant",
        "cmd",
        name="Via Command",
        domain=["CMD.test", "alt.test"],
        db_name=tenant_db_name("cmd"),
        stdout=None,
        verbosity=0,
    )
    client = Client.objects.get(slug="cmd")
    assert client.is_active
    assert list(ClientDomain.objects.filter(client=client).values_list("domain", "is_primary")) == [
        ("cmd.test", True),
        ("alt.test", False),
    ]


def test_provision_tenant_command_rejects_reserved_slug():
    with pytest.raises(CommandError, match="reserved"):
        call_command("provision_tenant", "default", name="x", db_name="x")


def test_provision_tenant_command_sets_strategy_and_params(tenant_db_name: Callable[[str], str]):
    call_command(
        "provision_tenant",
        "env",
        name="Env",
        db_name=tenant_db_name("env"),
        db_strategy="testutils.strategies.EnvironmentPassword",
        db_params='{"PASSWORD_ENV": "ENV_DB_PASSWORD", "OPTIONS": {}}',
        db_port="",
        skip_create_db=True,
        skip_migrate=True,
        verbosity=0,
    )
    client = Client.objects.get(slug="env")
    assert type(client.db_strategy).__name__ == "EnvironmentPassword"
    assert client.db_params == {"PASSWORD_ENV": "ENV_DB_PASSWORD", "OPTIONS": {}}

    call_command(
        "provision_tenant",
        "env",
        name="Env",
        db_name=client.db_name,
        db_host="db2",
        skip_create_db=True,
        skip_migrate=True,
        verbosity=0,
    )
    client.refresh_from_db()  # stored params kept, --db-host merged in, strategy unchanged
    assert client.db_params == {"PASSWORD_ENV": "ENV_DB_PASSWORD", "OPTIONS": {}, "HOST": "db2"}
    assert type(client.db_strategy).__name__ == "EnvironmentPassword"


@pytest.mark.parametrize(
    ("options", "message"),
    [
        ({"db_strategy": "testutils.strategies.Unregistered"}, "Unknown database strategy"),
        ({"db_params": "{not json"}, "not valid JSON"),
        ({"db_params": "[1, 2]"}, "must be a JSON object"),
        ({"db_params": '{"NAME": "x"}'}, "does not accept NAME"),
    ],
)
def test_provision_tenant_command_rejects_bad_database_options(options, message):
    with pytest.raises(CommandError, match=message):
        call_command("provision_tenant", "bad", name="x", db_name="x", **options)
    assert not Client.objects.filter(slug="bad").exists()


def test_migrate_tenants_command(acme, tenant_factory, capsys):
    tenant_factory("pending", provisioning=True, migrated=False)

    call_command("migrate_tenants", verbosity=0)

    out = capsys.readouterr().out
    assert "==> acme" in out
    assert "pending" not in out
    with tenant_context("acme"):
        from notes.models import Note

        assert Note.objects.count() == 0


def test_migrate_tenants_reports_failures(tenant_factory, capsys):
    bad = tenant_factory("bad", migrated=False)
    bad.db_name = "/nonexistent/dir/bad.sqlite3"
    bad.save()

    with pytest.raises(SystemExit) as exc:
        call_command("migrate_tenants", slug=["bad"], verbosity=0)
    assert exc.value.code == 1
    assert "failed" in capsys.readouterr().err
