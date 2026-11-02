"""Create two demo tenants, each with its own SQLite database and a user.

python manage.py migrate
python manage.py seed_demo
python manage.py runserver
# http://acme.localhost:8000/   (alice / demo)
# http://globex.localhost:8000/ (bob / demo)
"""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand

from django_db_tenants import tenant_context

TENANTS = (
    ("acme", "ACME S.p.A.", "alice"),
    ("globex", "Globex Corporation", "bob"),
)


class Command(BaseCommand):
    help = "Provision the 'acme' and 'globex' demo tenants (idempotent)."

    def handle(self, *args, **options) -> None:
        for slug, name, username in TENANTS:
            # The library's own command: Client + ClientDomain rows, CREATE DATABASE, migrate, activate.
            call_command(
                "provision_tenant",
                slug,
                name=name,
                domain=[f"{slug}.localhost"],
                db_name=str(settings.VAR_DIR / f"{slug}.sqlite3"),
                stdout=self.stdout,
            )
            with tenant_context(slug):  # users live in the tenant database
                users = get_user_model()._default_manager
                if not users.filter(username=username).exists():
                    users.create_user(username, f"{username}@{slug}.localhost", "demo")  # ty: ignore[unresolved-attribute]
            self.stdout.write(f"  http://{slug}.localhost:8000/  user={username} password=demo")
