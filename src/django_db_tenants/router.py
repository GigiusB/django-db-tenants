"""Database router: shared apps -> template DB, everything else -> current tenant."""

from .conf import app_settings
from .context import get_current_tenant_alias


class TenantRouter:
    @staticmethod
    def _shared(app_label: str) -> bool:
        return app_label in set(app_settings.SHARED_APPS)

    def _db_for(self, model):
        if self._shared(model._meta.app_label):
            return app_settings.TEMPLATE_ALIAS
        return get_current_tenant_alias() or app_settings.TEMPLATE_ALIAS

    def db_for_read(self, model, **hints):
        return self._db_for(model)

    def db_for_write(self, model, **hints):
        return self._db_for(model)

    def allow_relation(self, obj1, obj2, **hints):
        db1, db2 = obj1._state.db, obj2._state.db
        if db1 and db2 and db1 != db2:
            return False
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if self._shared(app_label):
            return db == app_settings.TEMPLATE_ALIAS
        if db == app_settings.TEMPLATE_ALIAS:
            return app_settings.TENANT_APPS_ON_DEFAULT
        return True
