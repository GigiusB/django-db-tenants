"""Runtime registration of tenant databases.

Django consults `connections.databases` (the live settings dict) every time it
opens a connection, and connections are created lazily. Adding an entry to that
dict is therefore enough to make a new alias usable — no restart required.

The connection settings come from the client's database strategy
(``client.db_strategy``, see ``strategies.py``).

Registration is per process: each worker registers an alias the first time it
needs it. `config_version()` lets a process notice that a client's connection
details changed (e.g. password rotation) and re-register.
"""

import copy
import logging
import threading

from django.db import connections

from .conf import app_settings

log = logging.getLogger(__name__)

_lock = threading.Lock()
_registered_versions: dict[str, str] = {}


def _registry() -> dict:
    # `connections.settings` is the dict Django keeps for the lifetime of the
    # process; `connections.databases` is the backward-compatible name for it.
    return connections.settings


def is_registered(alias: str) -> bool:
    return alias in _registry()


def ensure_db_registered(client, force: bool = False) -> str:
    """Make `client.alias` usable with `connections[alias]` / `.using(alias)`."""
    alias = client.alias
    version = client.config_version()

    if not force and _registered_versions.get(alias) == version and alias in _registry():
        return alias

    with _lock:
        if not force and _registered_versions.get(alias) == version and alias in _registry():
            return alias

        cfg = client.get_db_strategy().connection_settings(copy.deepcopy(_registry()[app_settings.TEMPLATE_ALIAS]))
        # Never reuse the template's TEST name for a tenant, whatever the strategy returned.
        cfg["TEST"] = {**cfg.get("TEST", {}), "NAME": None}

        _registry()[alias] = cfg
        _registered_versions[alias] = version
        # Drop any connection this thread already holds for the alias so the new
        # settings take effect immediately.
        _close_thread_connection(alias)
        log.info("Registered tenant database alias %r", alias)
    return alias


def unregister_db(alias: str) -> None:
    with _lock:
        _close_thread_connection(alias)
        _registry().pop(alias, None)
        _registered_versions.pop(alias, None)


def _close_thread_connection(alias: str) -> None:
    try:
        conn = getattr(connections._connections, alias)  # ty: ignore[missing-attribute] - thread-local store
    except AttributeError:
        return
    try:
        conn.close()
    finally:
        try:
            del connections[alias]
        except (AttributeError, TypeError):  # pragma: no cover - older Django without __delitem__
            delattr(connections._connections, alias)  # ty: ignore[missing-attribute]
