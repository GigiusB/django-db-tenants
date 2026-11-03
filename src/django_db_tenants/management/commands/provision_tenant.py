import json

from django.core.management.base import BaseCommand, CommandError

from django_db_tenants.conf import app_settings
from django_db_tenants.models import Client, ClientDomain
from django_db_tenants.provisioning import provision
from django_db_tenants.strategies import registry

# --db-<option> shortcuts for db_params keys (the keys of the built-in TemplateOverlay strategy).
PARAM_OPTIONS = {
    "db_engine": "ENGINE",
    "db_host": "HOST",
    "db_port": "PORT",
    "db_user": "USER",
    "db_password": "PASSWORD",
}


class Command(BaseCommand):
    help = "Create (or update) a client, create its database, migrate it and activate it. No restart needed."

    def add_arguments(self, parser):
        parser.add_argument("slug")
        parser.add_argument("--name", required=True)
        parser.add_argument("--domain", action="append", default=[], help="Repeatable. First one is primary.")
        parser.add_argument("--db-name", required=True)
        parser.add_argument(
            "--db-strategy",
            default="",
            help="Dotted path of a registered database strategy (default: keep / built-in).",
        )
        parser.add_argument(
            "--db-params", default="", help="JSON object merged into the client's db_params (strategy parameters)."
        )
        for option, key in PARAM_OPTIONS.items():
            parser.add_argument(f"--{option.replace('_', '-')}", default="", help=f"Sets db_params {key}.")
        parser.add_argument("--skip-create-db", action="store_true")
        parser.add_argument("--skip-migrate", action="store_true")

    def handle(self, *args, **o):
        using = app_settings.TEMPLATE_ALIAS
        if o["db_strategy"] and o["db_strategy"] not in registry:
            choices = ", ".join(path for path, _ in registry.as_choices())
            raise CommandError(f"Unknown database strategy {o['db_strategy']!r}. Registered: {choices}")
        params = self._params(o)

        # Not get_or_create: a new client is saved only after it passes validation.
        client = Client.objects.using(using).filter(slug=o["slug"]).first() or Client(slug=o["slug"])
        created = client.pk is None
        client.name = o["name"]
        client.db_name = o["db_name"]
        if o["db_strategy"]:
            client.db_strategy = o["db_strategy"]
        client.db_params = {**(client.db_params or {}), **params}
        try:
            client.full_clean()
        except Exception as exc:
            raise CommandError(str(exc)) from exc
        client.save(using=using)

        for i, domain in enumerate(o["domain"]):
            ClientDomain.objects.using(using).update_or_create(
                domain=domain.lower(), defaults={"client": client, "is_primary": i == 0}
            )

        provision(client, create_db=not o["skip_create_db"], migrate=not o["skip_migrate"])
        self.stdout.write(
            self.style.SUCCESS(f"{'Created' if created else 'Updated'} and provisioned tenant '{client.slug}'.")
        )

    @staticmethod
    def _params(o) -> dict:
        params = {}
        if o["db_params"]:
            try:
                params = json.loads(o["db_params"])
            except ValueError as exc:
                raise CommandError(f"--db-params is not valid JSON: {exc}") from exc
            if not isinstance(params, dict):
                raise CommandError("--db-params must be a JSON object")
        for option, key in PARAM_OPTIONS.items():
            if o[option]:
                params[key] = o[option]
        return params
