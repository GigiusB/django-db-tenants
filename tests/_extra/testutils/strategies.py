"""Database strategies used by the tests (registered through DB_TENANTS["DATABASE_STRATEGIES"])."""

import os
from typing import Any

from django.core.exceptions import ImproperlyConfigured

from django_db_tenants.strategies import TemplateOverlay


class EnvironmentPassword(TemplateOverlay):
    """TemplateOverlay whose password comes from the environment variable named by ``PASSWORD_ENV``."""

    label = "Template + password from environment"
    param_keys = TemplateOverlay.settings_keys - {"PASSWORD"} | {"PASSWORD_ENV", "MAINTENANCE_DB"}

    def connection_settings(self, template: dict[str, Any]) -> dict[str, Any]:
        settings = super().connection_settings(template)
        variable = self.params.get("PASSWORD_ENV")
        if variable:
            try:
                settings["PASSWORD"] = os.environ[variable]
            except KeyError:
                raise ImproperlyConfigured(f"{variable} is not set") from None
        return settings


class Unregistered(TemplateOverlay):
    """A valid strategy class that is deliberately not in the registry."""
