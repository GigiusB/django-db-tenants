from django.contrib.auth import get_user_model
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render

from django_db_tenants import get_current_tenant


def home(request: HttpRequest) -> HttpResponse:
    # `request.tenant` is set by TenantMiddleware; get_current_tenant() works anywhere
    # in the call stack (models, services, signals) without passing the request around.
    return render(request, "home.html", {"tenant": get_current_tenant()})


def whoami(request: HttpRequest) -> JsonResponse:
    """Which database served this request? Handy for checking the routing."""
    tenant = getattr(request, "tenant", None)
    return JsonResponse(
        {
            "tenant": tenant.slug if tenant else None,
            "users": get_user_model().objects.count(),
        }
    )


def healthz(request: HttpRequest) -> HttpResponse:
    # Listed in DB_TENANTS["EXEMPT_PATHS"] (the default), so no tenant lookup happens.
    return HttpResponse("ok", content_type="text/plain")
