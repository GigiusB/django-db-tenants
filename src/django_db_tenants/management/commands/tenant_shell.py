from django.core.management import call_command
from django.core.management.base import BaseCommand

from django_db_tenants.context import tenant_context


class Command(BaseCommand):
    help = "Open a Django shell with a tenant activated: manage.py tenant_shell acme"

    def add_arguments(self, parser):
        parser.add_argument("slug")

    def handle(self, slug, **options):
        with tenant_context(slug):
            self.stdout.write(self.style.NOTICE(f"Tenant '{slug}' active."))
            call_command("shell")
