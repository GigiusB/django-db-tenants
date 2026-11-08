"""Request -> Client resolvers. Pick one via DB_TENANTS["RESOLVER"]."""

from .conf import app_settings
from .registry import get_client, get_client_for_host


def resolve_by_host(request):
    """Map the request's host name to a ClientDomain. Control hosts get no tenant."""
    host = request.get_host().split(":")[0].lower()
    if host in {h.lower() for h in app_settings.CONTROL_HOSTS}:
        return None
    return get_client_for_host(host)


def resolve_by_header(request, header="HTTP_X_TENANT"):
    """For APIs behind a gateway that injects an X-Tenant: <slug> header."""
    slug = request.META.get(header)
    if not slug:
        return None
    return get_client(slug)
