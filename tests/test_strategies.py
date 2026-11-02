import pickle

import pytest
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db import connection, connections
from django.db.migrations.executor import MigrationExecutor

from django_db_tenants.admin import ClientForm
from django_db_tenants.db import ensure_db_registered
from django_db_tenants.models import Client
from django_db_tenants.strategies import DEFAULT_STRATEGY, TemplateOverlay, registry, template_settings
from testutils.factories import ClientFactory
from testutils.strategies import EnvironmentPassword

pytestmark = pytest.mark.django_db


def test_default_strategy_is_template_overlay_bound_to_the_client():
    client = ClientFactory.build()
    assert isinstance(client.db_strategy, TemplateOverlay)
    assert client.db_strategy.client is client
    assert DEFAULT_STRATEGY in registry


def test_template_overlay_settings():
    client = ClientFactory.build(
        db_name="acme_db",
        db_params={"HOST": "db2", "USER": "", "MAINTENANCE_DB": "template1", "OPTIONS": {"connect_timeout": 3}},
    )
    template = template_settings()
    cfg = client.db_strategy.connection_settings(template_settings())

    assert (cfg["NAME"], cfg["HOST"], cfg["USER"]) == ("acme_db", "db2", template["USER"])
    assert cfg["OPTIONS"] == {**template["OPTIONS"], "connect_timeout": 3}
    assert "MAINTENANCE_DB" not in cfg


def test_strategies_from_settings_are_registered():
    assert "testutils.strategies.EnvironmentPassword" in registry
    assert "testutils.strategies.Unregistered" not in registry


def test_unregistered_strategy_is_rejected():
    with pytest.raises(ValidationError) as exc:
        ClientFactory.build(db_strategy="testutils.strategies.Unregistered").full_clean()
    assert "db_strategy" in exc.value.message_dict


def test_custom_strategy_drives_registration(monkeypatch):
    monkeypatch.setenv("ACME_DB_PASSWORD", "from-env")
    client = ClientFactory.create(
        slug="envy",
        db_strategy="testutils.strategies.EnvironmentPassword",
        db_params={"PASSWORD_ENV": "ACME_DB_PASSWORD"},
    )
    client.full_clean()
    client.refresh_from_db()
    assert isinstance(client.db_strategy, EnvironmentPassword)

    ensure_db_registered(client)

    assert connections.settings["envy"]["PASSWORD"] == "from-env"
    assert "PASSWORD_ENV" not in connections.settings["envy"]


def test_custom_strategy_keys_are_validated():
    with pytest.raises(ValidationError, match="does not accept PASSWORD"):
        ClientFactory.build(db_strategy="testutils.strategies.EnvironmentPassword", db_params={"PASSWORD": "x"}).clean()


def test_missing_strategy_class_fails_on_use_only():
    client = ClientFactory.create()
    with connection.cursor() as cur:
        cur.execute(
            "UPDATE django_db_tenants_client SET db_strategy = 'gone.module.Strategy' WHERE id = %s", [client.pk]
        )
    client = Client.objects.get(pk=client.pk)  # the row still loads
    with pytest.raises(ImproperlyConfigured, match=r"gone\.module\.Strategy"):
        client.get_db_strategy()


def test_client_with_strategy_survives_the_cache():
    client = ClientFactory.create(db_params={"HOST": "h"})
    copy = pickle.loads(pickle.dumps(client))  # noqa: S301 - our own object, round-tripped as the cache does
    assert isinstance(copy.db_strategy, TemplateOverlay)
    assert copy.db_strategy.params == {"HOST": "h"}


def test_admin_form_edits_strategy_and_params():
    data = {
        "name": "Form",
        "slug": "form",
        "status": Client.Status.ACTIVE,
        "db_strategy": "testutils.strategies.EnvironmentPassword",
        "db_name": "form_db",
        "db_params": '{"PASSWORD_ENV": "X"}',
        "oidc_scopes": "openid",
    }
    form = ClientForm(data=data)
    assert form.is_valid(), form.errors
    client = form.save()
    client.refresh_from_db()
    assert isinstance(client.db_strategy, EnvironmentPassword)
    assert client.db_params == {"PASSWORD_ENV": "X"}

    form = ClientForm(data={**data, "slug": "form2", "db_params": '{"PASSWORD": "x"}'})
    assert not form.is_valid()
    assert "db_params" in form.errors


@pytest.mark.django_db(transaction=True)
def test_migration_moves_connection_columns_into_db_params():
    before, after = [("django_db_tenants", "0001_initial")], [("django_db_tenants", "0003_remove_client_db_columns")]
    executor = MigrationExecutor(connection)
    executor.migrate(before)
    OldClient = executor.loader.project_state(before).apps.get_model("django_db_tenants", "Client")
    OldClient.objects.create(
        name="Old", slug="old", db_name="old_db", db_host="h", db_port="", db_password="pw", db_options={"a": 1}
    )
    OldClient.objects.create(name="Plain", slug="plain", db_name="plain_db")

    executor = MigrationExecutor(connection)
    executor.migrate(after)

    assert Client.objects.get(slug="old").db_params == {"HOST": "h", "PASSWORD": "pw", "OPTIONS": {"a": 1}}
    assert Client.objects.get(slug="plain").db_params == {}
    assert isinstance(Client.objects.get(slug="old").db_strategy, TemplateOverlay)

    executor = MigrationExecutor(connection)
    executor.migrate(before)  # and back
    OldClient = executor.loader.project_state(before).apps.get_model("django_db_tenants", "Client")
    old = OldClient.objects.get(slug="old")
    assert (old.db_host, old.db_port, old.db_password, old.db_options) == ("h", "", "pw", {"a": 1})

    MigrationExecutor(connection).migrate(after)
