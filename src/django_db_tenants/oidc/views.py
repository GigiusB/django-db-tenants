from urllib.parse import urlencode

from django.contrib import auth
from django.http import Http404, HttpRequest, HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods

from .client import get_oidc_client
from .conf import oidc_settings
from .strategy import get_oidc_config

SESSION_ID_TOKEN = "db_tenants_sso_id_token"  # noqa: S105 - a session key, not a secret
SESSION_NEXT = "db_tenants_sso_next"


def _uses_oidc(client) -> bool:
    return client is not None and get_oidc_config(client) is not None


def _tenant(request):
    client = getattr(request, "tenant", None)
    if not _uses_oidc(client):
        raise Http404("SSO is not available for this host.")
    return client


def _safe_next(request, url):
    if url and url_has_allowed_host_and_scheme(
        url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return url
    return None


@require_http_methods(["GET"])  # same as @require_GET, which ty cannot type yet
def login(request: HttpRequest) -> HttpResponse:
    client = _tenant(request)
    oidc = get_oidc_client(client)
    request.session[SESSION_NEXT] = _safe_next(request, request.GET.get("next"))
    redirect_uri = request.build_absolute_uri(reverse("db_tenants_oidc:callback"))
    return oidc.authorize_redirect(request, redirect_uri)


@require_http_methods(["GET"])  # same as @require_GET, which ty cannot type yet
def callback(request: HttpRequest) -> HttpResponse:
    client = _tenant(request)
    if "error" in request.GET:
        return HttpResponseBadRequest(f"SSO error: {request.GET.get('error_description') or request.GET['error']}")

    oidc = get_oidc_client(client)
    token = oidc.authorize_access_token(request)  # validates state, nonce, id_token signature
    userinfo = token.get("userinfo") or oidc.userinfo(token=token)

    user = oidc_settings.USER_SYNC(client, dict(userinfo), request)
    if user is None:
        return HttpResponseForbidden("Your account is not allowed to sign in here.")

    auth.login(request, user, backend=oidc_settings.AUTH_BACKEND)
    request.session[SESSION_ID_TOKEN] = token.get("id_token")
    next_url = request.session.pop(SESSION_NEXT, None) or oidc_settings.LOGIN_REDIRECT_URL
    return redirect(next_url)


@require_http_methods(["GET", "POST"])
def logout(request: HttpRequest) -> HttpResponse:
    client = getattr(request, "tenant", None)
    id_token = request.session.get(SESSION_ID_TOKEN)
    auth.logout(request)

    post_logout = request.build_absolute_uri(oidc_settings.LOGOUT_REDIRECT_URL)
    if _uses_oidc(client) and oidc_settings.RP_INITIATED_LOGOUT and id_token:
        metadata = get_oidc_client(client).load_server_metadata()
        end_session = metadata.get("end_session_endpoint")
        if end_session:
            params = urlencode({"id_token_hint": id_token, "post_logout_redirect_uri": post_logout})
            return redirect(f"{end_session}?{params}")
    return redirect(post_logout)
