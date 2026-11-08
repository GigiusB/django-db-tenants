"""django-db-tenants: database-per-client multi-tenancy for Django.

Public API (import from here):

    from django_db_tenants import get_current_tenant, tenant_context, ensure_db_registered
"""

__version__ = "0.2.0"

from .context import get_current_tenant, get_current_tenant_alias, tenant_context  # noqa: F401
from .db import ensure_db_registered  # noqa: F401
