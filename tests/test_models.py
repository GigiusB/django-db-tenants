import pytest
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db import connection
from freezegun import freeze_time

from testutils.factories import ClientFactory

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("slug", ["default"])
def test_reserved_slug_is_invalid(slug):
    with pytest.raises(ValidationError, match="reserved"):
        ClientFactory.build(slug=slug).full_clean()


def test_db_params_are_validated_by_the_strategy():
    with pytest.raises(ValidationError, match="does not accept NAME"):
        ClientFactory.build(db_params={"NAME": "other"}).full_clean()
    with pytest.raises(ValidationError, match="OPTIONS must be a JSON object"):
        ClientFactory.build(db_params={"OPTIONS": "sslmode=require"}).full_clean()
    ClientFactory.build(db_params={"HOST": "db2", "OPTIONS": {"sslmode": "require"}}).full_clean()


@freeze_time("2026-03-04 05:06:07")
def test_config_version_tracks_updated_at():
    assert ClientFactory.build().config_version() == ""
    assert ClientFactory.create().config_version() == "2026-03-04T05:06:07+00:00"


def test_secrets_are_encrypted_at_rest():
    params = {"USER": "shh", "PASSWORD": "s3cret"}
    client = ClientFactory.create(db_params=params)
    client.refresh_from_db()
    assert client.db_params == params

    with connection.cursor() as cur:
        cur.execute("SELECT db_params FROM django_db_tenants_client WHERE id = %s", [client.pk])
        (raw,) = cur.fetchone()
    assert "s3cret" not in raw
    assert "shh" not in raw


def test_legacy_plaintext_is_returned_as_is():
    client = ClientFactory.create()
    with connection.cursor() as cur:
        cur.execute("UPDATE django_db_tenants_client SET db_params = %s WHERE id = %s", ['{"HOST": "h"}', client.pk])
    client.refresh_from_db()
    assert client.db_params == {"HOST": "h"}


def test_undecryptable_params_fail_for_that_client_only():
    client = ClientFactory.create()
    with connection.cursor() as cur:
        cur.execute("UPDATE django_db_tenants_client SET db_params = 'garbage' WHERE id = %s", [client.pk])
    client.refresh_from_db()  # the row still loads
    with pytest.raises(ImproperlyConfigured, match="not a JSON object"):
        _ = client.get_db_strategy().params
    with pytest.raises(ValidationError, match="Must be a JSON object"):
        client.full_clean()
