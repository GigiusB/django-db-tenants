"""Resolve the tenant for each request and activate it for the request's lifetime.

Place BEFORE django.contrib.sessions and django.contrib.auth middleware so that
session and user lookups are already routed to the tenant database.
"""

import logging

from asgiref.sync import iscoroutinefunction, markcoroutinefunction, sync_to_async
from django.http import HttpResponseNotFound

from .conf import app_settings
from .context import reset_current_tenant, set_current_tenant
from .db import ensure_db_registered
from .exceptions import TenantError

log = logging.getLogger(__name__)


class TenantMiddleware:
    sync_capable = True
    async_capable = True

    def __init__(self, get_response):
        self.get_response = get_response
        # asgiref's helpers (as Django's own MiddlewareMixin uses) until Python 3.12 is the floor.
        self._is_async = iscoroutinefunction(get_response)  # ty: ignore[deprecated]
        if self._is_async:
            markcoroutinefunction(self)  # ty: ignore[invalid-argument-type]

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _is_exempt(request) -> bool:
        return any(request.path.startswith(p) for p in app_settings.EXEMPT_PATHS)

    @staticmethod
    def _resolve(request):
        """Returns (client|None, error_response|None)."""
        try:
            client = app_settings.RESOLVER(request)
        except TenantError as exc:
            handler = app_settings.NOT_FOUND_HANDLER
            if handler:
                return None, handler(request, exc)
            log.info("No tenant for %s: %s", request.get_host(), exc)
            return None, HttpResponseNotFound("Unknown tenant.")
        if client is not None:
            ensure_db_registered(client)
        return client, None

    # --------------------------------------------------------------------- sync
    def __call__(self, request):
        if self._is_async:
            return self.__acall__(request)

        if self._is_exempt(request):
            request.tenant = None
            return self.get_response(request)

        client, error = self._resolve(request)
        if error is not None:
            return error

        request.tenant = client
        token = set_current_tenant(client)
        try:
            return self.get_response(request)
        finally:
            reset_current_tenant(token)

    # -------------------------------------------------------------------- async
    async def __acall__(self, request):
        if self._is_exempt(request):
            request.tenant = None
            return await self.get_response(request)

        client, error = await sync_to_async(self._resolve, thread_sensitive=True)(request)
        if error is not None:
            return error

        request.tenant = client
        token = set_current_tenant(client)
        try:
            return await self.get_response(request)
        finally:
            reset_current_tenant(token)
