from django.apps import AppConfig


class KtDbTenantsConfig(AppConfig):
    name = "django_db_tenants"
    label = "django_db_tenants"
    verbose_name = "DB Tenants"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        from . import signals  # noqa: F401
        from .conf import app_settings
        from .strategies import registry

        for strategy in app_settings.DATABASE_STRATEGIES:
            registry.register(strategy)
