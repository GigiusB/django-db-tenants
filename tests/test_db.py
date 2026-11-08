from datetime import timedelta

import pytest
from django.db import connections
from freezegun import freeze_time

from django_db_tenants.db import ensure_db_registered, is_registered, unregister_db
from testutils.factories import ClientFactory

pytestmark = pytest.mark.django_db


def test_registration_overlays_client_settings_on_template():
    client = ClientFactory.create(
        slug="remote",
        db_name="remote_db",
        db_params={"HOST": "db.example.com", "USER": "u", "PASSWORD": "p", "PORT": "", "OPTIONS": {"timeout": 5}},
    )
    alias = ensure_db_registered(client)

    cfg = connections.settings[alias]
    template = connections.settings["default"]
    assert alias == "remote"
    assert cfg["ENGINE"] == template["ENGINE"]
    assert cfg["PORT"] == template["PORT"]  # empty values inherit the template's
    assert (cfg["NAME"], cfg["HOST"], cfg["USER"], cfg["PASSWORD"]) == ("remote_db", "db.example.com", "u", "p")
    assert cfg["OPTIONS"]["timeout"] == 5
    assert cfg["TEST"]["NAME"] is None


def test_registration_is_cached_until_client_changes():
    with freeze_time("2026-01-01 12:00") as frozen:
        client = ClientFactory.create(slug="acme", db_name="one")
        ensure_db_registered(client)
        cfg = connections.settings["acme"]

        ensure_db_registered(client)
        assert connections.settings["acme"] is cfg  # same version: untouched

        frozen.tick(timedelta(seconds=1))
        client.db_name = "two"
        client.save()  # bumps updated_at -> config_version
        ensure_db_registered(client)
        assert connections.settings["acme"]["NAME"] == "two"


def test_force_re_registers():
    client = ClientFactory.create(slug="acme", db_name="one")
    ensure_db_registered(client)
    client.db_name = "two"  # not saved: version unchanged
    ensure_db_registered(client)
    assert connections.settings["acme"]["NAME"] == "one"
    ensure_db_registered(client, force=True)
    assert connections.settings["acme"]["NAME"] == "two"


def test_unregister(acme):
    ensure_db_registered(acme)
    connections["acme"].ensure_connection()
    unregister_db("acme")
    assert not is_registered("acme")
    unregister_db("acme")  # idempotent


def test_deleting_client_unregisters_alias(acme):
    ensure_db_registered(acme)
    acme.delete()
    assert not is_registered("acme")
