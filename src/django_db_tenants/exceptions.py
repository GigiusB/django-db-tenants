class TenantError(Exception):
    """Base class for django_db_tenants errors."""


class TenantNotFound(TenantError):
    """No active client matches the incoming request."""


class TenantInactive(TenantError):
    """The client exists but is not ACTIVE."""
