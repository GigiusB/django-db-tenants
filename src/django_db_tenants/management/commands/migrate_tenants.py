from django.core.management.base import BaseCommand

from django_db_tenants.conf import app_settings
from django_db_tenants.models import Client
from django_db_tenants.provisioning import migrate_tenant


class Command(BaseCommand):
    help = "Run migrations on every tenant database (or on one with --slug). Run after `migrate` on the shared DB."

    def add_arguments(self, parser):
        parser.add_argument("--slug", action="append", default=[], help="Only these tenants (repeatable).")
        parser.add_argument("--include-inactive", action="store_true")
        parser.add_argument("--fake", action="store_true")

    def handle(self, *args, **o):
        qs = Client.objects.using(app_settings.TEMPLATE_ALIAS).all()
        if o["slug"]:
            qs = qs.filter(slug__in=o["slug"])
        elif not o["include_inactive"]:
            qs = qs.filter(status=Client.Status.ACTIVE)

        failures = 0
        for client in qs:
            self.stdout.write(f"==> {client.slug}")
            try:
                migrate_tenant(client, fake=o["fake"], verbosity=o["verbosity"])
            except Exception as exc:  # noqa: BLE001
                failures += 1
                self.stderr.write(self.style.ERROR(f"    failed: {exc}"))
        if failures:
            raise SystemExit(1)
        self.stdout.write(self.style.SUCCESS("All tenants migrated."))
