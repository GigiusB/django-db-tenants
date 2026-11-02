"""Per-request / per-task tenant context.

A ContextVar (not threading.local) so it is correct under threads, asyncio and
asgiref's sync_to_async / async_to_sync bridging.
"""

from contextlib import contextmanager
from contextvars import ContextVar
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import Client

_current: ContextVar["Client | None"] = ContextVar("django_db_tenants.current", default=None)


def get_current_tenant() -> "Client | None":
    """Return the current Client, or None (shared DB)."""
    return _current.get()


def get_current_tenant_alias() -> str | None:
    client = _current.get()
    return client.alias if client is not None else None


def set_current_tenant(client):
    return _current.set(client)


def reset_current_tenant(token):
    _current.reset(token)


@contextmanager
def tenant_context(client_or_slug):
    """Run a block as a tenant. Accepts a Client or its slug; None = shared DB.

    with tenant_context("acme"):
        Order.objects.count()   # routed to the 'acme' database
    """
    from .db import ensure_db_registered
    from .registry import get_client

    client = client_or_slug
    if isinstance(client_or_slug, str):
        client = get_client(client_or_slug)
    if client is not None:
        ensure_db_registered(client)
    token = _current.set(client)
    try:
        yield client
    finally:
        _current.reset(token)
