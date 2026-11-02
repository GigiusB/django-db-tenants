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


def test_sso_requires_issuer_and_client_id():
    with pytest.raises(ValidationError, match="SSO requires"):
        ClientFactory.build(sso_enabled=True).full_clean()
    ClientFactory.build(sso=True).full_clean()


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
    client = ClientFactory.create(db_params={"PASSWORD": "s3cret"}, oidc_client_secret="shh")
    client.refresh_from_db()
    assert (client.db_params, client.oidc_client_secret) == ({"PASSWORD": "s3cret"}, "shh")

    with connection.cursor() as cur:
        cur.execute("SELECT db_params, oidc_client_secret FROM django_db_tenants_client WHERE id = %s", [client.pk])
        raw = cur.fetchone()
    assert "s3cret" not in raw[0]
    assert "shh" not in raw[1]


def test_legacy_plaintext_is_returned_as_is():
    client = ClientFactory.create()
    with connection.cursor() as cur:
        cur.execute(
            "UPDATE django_db_tenants_client SET oidc_client_secret = 'plain', db_params = %s WHERE id = %s",
            ['{"HOST": "h"}', client.pk],
        )
    client.refresh_from_db()
    assert client.oidc_client_secret == "plain"
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
