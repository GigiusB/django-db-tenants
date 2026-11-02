"""Create, migrate and drop tenant databases at runtime.

The database work itself is done by the client's database strategy
(``client.db_strategy``, see ``strategies.py``).
"""

from django.core.management import call_command

from .conf import app_settings
from .db import ensure_db_registered, unregister_db
from .models import Client


def create_database(client: Client, if_not_exists: bool = True) -> bool:
    """Create the tenant's database through its strategy. Returns True if it was created."""
    return client.get_db_strategy().create_database(if_not_exists=if_not_exists)


def drop_database(client: Client) -> None:
    """Drop the tenant's database through its strategy, after closing this thread's connection to it.

    The client row is left alone: delete it, or set it back to PROVISIONING, yourself.
    """
    unregister_db(client.alias)
    client.get_db_strategy().drop_database()


def migrate_tenant(client: Client, **options) -> None:
    alias = ensure_db_registered(client)
    call_command("migrate", database=alias, interactive=False, **options)


def provision(client: Client, create_db: bool = True, migrate: bool = True, activate: bool = True) -> Client:
    """Full onboarding: create DB, migrate, mark ACTIVE. Safe to re-run."""
    if create_db:
        create_database(client)
    if migrate:
        migrate_tenant(client)
    if activate and client.status != Client.Status.ACTIVE:
        client.status = Client.Status.ACTIVE
        client.save(using=app_settings.TEMPLATE_ALIAS, update_fields=["status", "updated_at"])
    return client
