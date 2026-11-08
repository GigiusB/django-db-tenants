"""Cached lookups of Client rows from the shared database."""

from django.core.cache import caches

from .cache import SHARED_KEY_PREFIX
from .conf import app_settings
from .exceptions import TenantInactive, TenantNotFound
from .models import Client, ClientDomain

_MISS = "__db_tenants_miss__"


def _cache():
    return caches[app_settings.CACHE_ALIAS]


def _host_key(host: str) -> str:
    return f"{SHARED_KEY_PREFIX}host:{host}"  # never tenant-namespaced, see cache.py


def _slug_key(slug: str) -> str:
    return f"{SHARED_KEY_PREFIX}slug:{slug}"


def get_client_for_host(host: str) -> Client:
    host = host.lower()
    key = _host_key(host)
    cached = _cache().get(key)
    if cached == _MISS:
        raise TenantNotFound(host) from None
    if cached is not None:
        return _check_active(cached)

    try:
        domain = ClientDomain.objects.using(app_settings.TEMPLATE_ALIAS).select_related("client").get(domain=host)
    except ClientDomain.DoesNotExist:
        _cache().set(key, _MISS, app_settings.CACHE_TTL)
        raise TenantNotFound(host) from None

    _cache().set(key, domain.client, app_settings.CACHE_TTL)
    return _check_active(domain.client)


def get_client(slug: str) -> Client:
    key = _slug_key(slug)
    cached = _cache().get(key)
    if cached is not None and cached != _MISS:
        return cached
    try:
        client = Client.objects.using(app_settings.TEMPLATE_ALIAS).get(slug=slug)
    except Client.DoesNotExist:
        raise TenantNotFound(slug) from None
    _cache().set(key, client, app_settings.CACHE_TTL)
    return client


def invalidate(client: Client) -> None:
    keys = [_slug_key(client.slug)]
    keys += [_host_key(d.domain) for d in ClientDomain.objects.using(app_settings.TEMPLATE_ALIAS).filter(client=client)]
    _cache().delete_many(keys)


def invalidate_host(host: str) -> None:
    _cache().delete(_host_key(host.lower()))


def _check_active(client: Client) -> Client:
    if not client.is_active:
        raise TenantInactive(client.slug)
    return client
