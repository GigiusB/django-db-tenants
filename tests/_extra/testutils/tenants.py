"""Helpers for creating real tenant databases in tests and cleaning up after them.

Tenant databases use the same backend as the shared database (see
:mod:`testutils.databases`):

* SQLite: one file per tenant in the test's ``tmp_path``.
* PostgreSQL / MySQL: one ``test_tenant_<slug>_<random>`` database per tenant on
  the configured server, dropped when the test ends.

Migrating a fresh database for every test is slow, so
:func:`build_template_database` migrates one "golden" database per session and
:func:`clone_database` copies it for each tenant: a file copy on SQLite,
``CREATE DATABASE ... TEMPLATE`` on PostgreSQL and a table-by-table copy on
MySQL (which has no database templates).

Server databases are created and dropped on a private copy of the "default"
connection: ``CREATE DATABASE`` cannot run inside the test transaction on
PostgreSQL, and commits it implicitly on MySQL.
"""

import shutil
import uuid
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from django.core.cache import caches
from django.db import connections
from django.db.backends.utils import CursorWrapper

from django_db_tenants import crypto, db, tenant_context
from django_db_tenants.conf import app_settings
from django_db_tenants.models import Client
from django_db_tenants.provisioning import migrate_tenant
from django_db_tenants.sso import oidc

TEMPLATE_ALIAS = "test_template"
SERVER_DB_PREFIX = "test_tenant_"


def vendor() -> str:
    """``"sqlite"``, ``"postgresql"`` or ``"mysql"``: the backend tenant databases are created on."""
    return connections[app_settings.TEMPLATE_ALIAS].vendor


def new_database_name(slug: str, directory: Path) -> str:
    """A database name for a new tenant: a file in ``directory`` on SQLite, a unique server database otherwise."""
    if vendor() == "sqlite":
        return str(directory / f"{slug}.sqlite3")
    return f"{SERVER_DB_PREFIX}{slug[:40]}_{uuid.uuid4().hex[:8]}"


@contextmanager
def _admin_cursor() -> Generator[CursorWrapper]:
    conn = connections[app_settings.TEMPLATE_ALIAS].copy()
    try:
        with conn.cursor() as cursor:
            yield cursor
    finally:
        conn.close()


def _quote(name: str) -> str:
    return connections[app_settings.TEMPLATE_ALIAS].ops.quote_name(name)


def create_empty_database(name: str) -> None:
    """Create an empty tenant database (on SQLite the file appears on first connect)."""
    if vendor() == "sqlite":
        return
    charset = " CHARACTER SET utf8mb4" if vendor() == "mysql" else ""
    with _admin_cursor() as cursor:
        cursor.execute(f"CREATE DATABASE {_quote(name)}{charset}")


def drop_database(name: str) -> None:
    """Drop a server database if it exists. SQLite files live in ``tmp_path`` and need no cleanup."""
    if vendor() == "sqlite":
        return
    force = " WITH (FORCE)" if vendor() == "postgresql" else ""  # PostgreSQL >= 13
    with _admin_cursor() as cursor:
        cursor.execute(f"DROP DATABASE IF EXISTS {_quote(name)}{force}")


def build_template_database(name: str) -> str:
    """Create and fully migrate the tenant database ``name``, replacing any leftover from an earlier run."""
    drop_database(name)
    create_empty_database(name)
    client = Client(slug=TEMPLATE_ALIAS, name="template", db_name=name)
    migrate_tenant(client, verbosity=0)
    db.unregister_db(client.alias)  # close the connection: the template must be idle to be copied
    return name


def clone_database(template: str, client: Client) -> None:
    """Give ``client`` a migrated database by copying the ``template`` database to ``client.db_name``."""
    match vendor():
        case "sqlite":
            shutil.copyfile(template, client.db_name)
        case "postgresql":
            with _admin_cursor() as cursor:
                cursor.execute(f"CREATE DATABASE {_quote(client.db_name)} TEMPLATE {_quote(template)}")
        case "mysql":
            _clone_mysql_database(template, client.db_name)
        case other:  # pragma: no cover
            raise NotImplementedError(f"clone_database not implemented for vendor {other!r}")


def _clone_mysql_database(template: str, target: str) -> None:
    with _admin_cursor() as cursor:
        cursor.execute(f"CREATE DATABASE {_quote(target)} CHARACTER SET utf8mb4")
        cursor.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = %s AND table_type = 'BASE TABLE'",
            [template],
        )
        tables = [row[0] for row in cursor.fetchall()]
        # SHOW CREATE TABLE keeps foreign keys (CREATE TABLE ... LIKE drops them); with the target as the
        # current database, the unqualified references in the DDL point at the copied tables.
        cursor.execute(f"USE {_quote(target)}")
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
        for table in tables:
            cursor.execute(f"SHOW CREATE TABLE {_quote(template)}.{_quote(table)}")
            cursor.execute(cursor.fetchone()[1])
            source = f"{_quote(template)}.{_quote(table)}"  # quoted identifiers from information_schema
            cursor.execute(f"INSERT INTO {_quote(table)} SELECT * FROM {source}")  # noqa: S608
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1")


def registered_tenant_aliases() -> list[str]:
    """Aliases that were added to ``connections`` at runtime by ``ensure_db_registered``."""
    return list(db._registered_versions)


def reset_tenant_state() -> None:
    """Undo all process-wide state the library accumulates.

    * runtime-registered connection aliases (and their open connections)
    * cached host/slug -> Client lookups
    * the cached Fernet instance (so ``settings`` overrides of the key apply)
    * per-tenant OIDC clients
    """
    for alias in registered_tenant_aliases():
        db.unregister_db(alias)
    for cache in caches.all():
        cache.clear()
    crypto.get_fernet.cache_clear()
    oidc._versions.clear()
    oidc._oauth = None


def tenant_login(http_client: Any, tenant: Client, user: Any) -> None:
    """``Client.force_login`` for a tenant user: the session is stored in the tenant's database."""
    with tenant_context(tenant):
        http_client.force_login(user)
