"""Helpers for background work (Celery, RQ, cron) which never passes through the middleware."""

import functools

from .context import tenant_context


def with_tenant(func):
    """Decorator: the wrapped callable must receive `tenant` (slug or Client) as a kwarg
    or first positional argument; the body runs inside that tenant's context.

        @shared_task
        @with_tenant
        def send_invoices(tenant):
            Invoice.objects.filter(sent=False)   # routed to the tenant DB
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        tenant = kwargs.get("tenant", args[0] if args else None)
        with tenant_context(tenant):
            return func(*args, **kwargs)

    return wrapper


def for_each_tenant(func, *, only_active=True):
    """Run `func(client)` for every tenant, inside each tenant's context."""
    from .conf import app_settings
    from .models import Client

    qs = Client.objects.using(app_settings.TEMPLATE_ALIAS).all()
    if only_active:
        qs = qs.filter(status=Client.Status.ACTIVE)
    results = {}
    for client in qs:
        with tenant_context(client):
            results[client.slug] = func(client)
    return results
