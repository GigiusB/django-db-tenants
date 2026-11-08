"""Background jobs never pass through the middleware, so they name their tenant.

With Celery this would be::

    @shared_task
    @with_tenant
    def purge_old_notes(tenant, days=30): ...

    purge_old_notes.delay(tenant="acme")
"""

from datetime import timedelta

from django.utils import timezone

from django_db_tenants.models import Client
from django_db_tenants.tasks import for_each_tenant, with_tenant

from .models import Note


@with_tenant
def purge_old_notes(tenant: str | Client, days: int = 30) -> int:
    """Delete the tenant's notes older than ``days``. Returns how many were removed."""
    cutoff = timezone.now() - timedelta(days=days)
    deleted, _ = Note.objects.filter(created_at__lt=cutoff).delete()
    return deleted


def notes_per_tenant() -> dict[str, int]:
    """Count notes in every active tenant database."""
    return for_each_tenant(lambda client: Note.objects.count())
