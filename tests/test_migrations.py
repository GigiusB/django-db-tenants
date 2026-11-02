import pytest
from django.core.management import call_command


@pytest.mark.django_db
def test_no_missing_migrations():
    call_command("makemigrations", "django_db_tenants", "notes", check=True, dry_run=True, verbosity=0)
