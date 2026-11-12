"""Database strategies: how a tenant's database is reached, created and dropped.

Every ``Client`` names its strategy in ``Client.db_strategy``, a django-strategy-field
``StrategyField`` holding the dotted path of a :class:`DatabaseStrategy` subclass from
:data:`registry`. Reading ``client.db_strategy`` returns an instance bound to the client.

A strategy reads its parameters from ``client.db_params`` (an encrypted JSON object
whose keys the strategy defines) and ``client.db_name``. Register your own strategies
with ``registry.register(MyStrategy)`` or ``DB_TENANTS["DATABASE_STRATEGIES"]``.
"""

import copy
import logging
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any

from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db import connections
from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.utils import load_backend
from strategy_field.registry import Registry

from .conf import app_settings

if TYPE_CHECKING:
    from .models import Client

log = logging.getLogger(__name__)

DEFAULT_STRATEGY = "django_db_tenants.strategies.TemplateOverlay"


def template_settings() -> dict[str, Any]:
    """A private copy of the template alias's connection settings."""
    return copy.deepcopy(connections.settings[app_settings.TEMPLATE_ALIAS])


class DatabaseStrategy:
    """Base class of database strategies.

    Subclasses implement :meth:`connection_settings` and, to support provisioning,
    :meth:`create_database` and :meth:`drop_database`.
    """

    #: Name shown in the admin and in validation errors.
    label = ""
    #: Keys accepted in ``Client.db_params``; ``None`` accepts any key.
    param_keys: frozenset[str] | None = None

    def __init__(self, client: "Client") -> None:
        self.client = client

    def __str__(self) -> str:
        return self.label or type(self).__name__

    @property
    def params(self) -> dict[str, Any]:
        """The client's ``db_params``, or an empty dict."""
        params = self.client.db_params or {}
        if not isinstance(params, dict):
            # Undecryptable (wrong ENCRYPTION_KEY) or not a JSON object.
            raise ImproperlyConfigured(f"db_params of client {self.client.slug!r} is not a JSON object")
        return params

    def validate(self) -> None:
        """Check ``client.db_params``; raise ``ValidationError`` on bad values. Called by ``Client.clean()``."""
        if not isinstance(self.client.db_params or {}, dict):
            raise ValidationError({"db_params": "Must be a JSON object."})
        if self.param_keys is None:
            return
        unknown = sorted(set(self.params) - self.param_keys)
        if unknown:
            raise ValidationError(
                {
                    "db_params": f"{self} does not accept {', '.join(unknown)}. "
                    f"Allowed keys: {', '.join(sorted(self.param_keys))}."
                }
            )

    def connection_settings(self, template: dict[str, Any]) -> dict[str, Any]:
        """Return the ``DATABASES`` entry of the tenant's database.

        ``template`` is a private deep copy of the template alias's settings (complete,
        with Django's defaults filled in): modify and return it, or build a new dict.
        """
        raise NotImplementedError

    def create_database(self, if_not_exists: bool = True) -> bool:
        """Create the tenant's database. Return ``True`` if it was created."""
        raise NotImplementedError(f"{self} cannot create databases")

    def drop_database(self) -> None:
        """Drop the tenant's database if it exists."""
        raise NotImplementedError(f"{self} cannot drop databases")


class TemplateOverlay(DatabaseStrategy):
    """The template connection with the client's parameters laid over it.

    ``db_params`` keys are ``DATABASES`` keys: ``ENGINE``, ``HOST``, ``PORT``, ``USER``,
    ``PASSWORD``, ``OPTIONS`` (merged into the template's), ``CONN_MAX_AGE``,
    ``CONN_HEALTH_CHECKS``, plus ``MAINTENANCE_DB``: the PostgreSQL database to connect
    to for ``CREATE`` / ``DROP DATABASE`` (default ``postgres``). Missing, empty and
    ``null`` values inherit the template's. ``NAME`` is ``client.db_name``.

    Databases are created and dropped on the server and with the account of the
    resulting connection, which needs the right to do so.
    """

    label = "Template connection + overrides"
    #: ``db_params`` keys copied into the connection settings.
    settings_keys = frozenset(
        {"ENGINE", "HOST", "PORT", "USER", "PASSWORD", "OPTIONS", "CONN_MAX_AGE", "CONN_HEALTH_CHECKS"}
    )
    param_keys = settings_keys | {"MAINTENANCE_DB"}

    def validate(self) -> None:
        super().validate()
        if not isinstance(self.params.get("OPTIONS") or {}, dict):
            raise ValidationError({"db_params": "OPTIONS must be a JSON object."})

    def connection_settings(self, template: dict[str, Any]) -> dict[str, Any]:
        overrides = {k: v for k, v in self.params.items() if k in self.settings_keys and v not in (None, "")}
        options = {**template.get("OPTIONS", {}), **overrides.pop("OPTIONS", {})}
        template.update(copy.deepcopy(overrides))
        template["OPTIONS"] = options
        template["NAME"] = self.client.db_name
        return template

    # -------------------------------------------------------------- lifecycle
    def _server(self, **changes: Any) -> BaseDatabaseWrapper:
        """An unregistered connection with this tenant's settings, for server-level commands."""
        settings = {**self.connection_settings(template_settings()), **changes}
        # Named after the template alias: the connection acts on behalf of the shared database.
        return load_backend(settings["ENGINE"]).DatabaseWrapper(settings, app_settings.TEMPLATE_ALIAS)

    def create_database(self, if_not_exists: bool = True) -> bool:
        server = self._server()
        match server.vendor:
            case "postgresql":
                name = server.settings_dict["NAME"]
                with self._postgres_cursor(server) as cursor:
                    cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", [name])
                    if cursor.fetchone():
                        if if_not_exists:
                            log.info("Database %s already exists", name)
                            return False
                        raise RuntimeError(f"Database {name} already exists")
                    cursor.execute(f"CREATE DATABASE {server.ops.quote_name(name)}")
                return True
            case "mysql":
                clause = "IF NOT EXISTS " if if_not_exists else ""
                name = server.ops.quote_name(server.settings_dict["NAME"])
                self._mysql_execute(f"CREATE DATABASE {clause}{name} CHARACTER SET utf8mb4")
                return True
            case "sqlite":
                return True  # the file is created on first connect
            case vendor:
                raise NotImplementedError(f"{self} cannot create databases on {vendor!r}")

    def drop_database(self) -> None:
        server = self._server()
        name = server.settings_dict["NAME"]
        match server.vendor:
            case "postgresql":
                with self._postgres_cursor(server) as cursor:
                    cursor.execute(f"DROP DATABASE IF EXISTS {server.ops.quote_name(name)}")
            case "mysql":
                self._mysql_execute(f"DROP DATABASE IF EXISTS {server.ops.quote_name(name)}")
            case "sqlite":
                if name and name != ":memory:" and not str(name).startswith("file:"):
                    Path(name).unlink(missing_ok=True)
            case vendor:
                raise NotImplementedError(f"{self} cannot drop databases on {vendor!r}")

    @contextmanager
    def _postgres_cursor(self, server: BaseDatabaseWrapper) -> Generator[Any]:
        """Autocommit cursor on the maintenance database: CREATE/DROP DATABASE cannot run in a transaction."""
        cfg = server.settings_dict
        conn = server.Database.connect(  # ty: ignore[missing-attribute] - psycopg or psycopg2, whichever Django loaded
            dbname=self.params.get("MAINTENANCE_DB") or "postgres",
            user=cfg.get("USER") or None,
            password=cfg.get("PASSWORD") or None,
            host=cfg.get("HOST") or None,
            port=cfg.get("PORT") or None,
        )
        try:
            conn.autocommit = True
            with conn.cursor() as cursor:
                yield cursor
        finally:
            conn.close()

    def _mysql_execute(self, sql: str) -> None:
        # A private connection without a default database (NAME ""): CREATE/DROP DATABASE commit
        # implicitly, so a transaction the caller has open elsewhere is left alone.
        conn = self._server(NAME="")
        try:
            with conn.cursor() as cursor:
                cursor.execute(sql)
        finally:
            conn.close()


#: The strategies a ``Client`` may use. Labels come from ``DatabaseStrategy.label``.
registry = Registry(DatabaseStrategy, label_attribute="label")
registry.register(TemplateOverlay)
