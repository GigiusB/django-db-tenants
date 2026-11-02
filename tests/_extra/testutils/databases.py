"""Choose the database backend the test suite runs against.

``TEST_DB`` picks the backend of the shared ("default") database, and with it
the backend of every tenant database, because tenant connections are copies of
"default"::

    TEST_DB=sqlite   # default: no server needed
    TEST_DB=pg       # TEST_PG_HOST / _PORT / _USER / _PASSWORD / _NAME
    TEST_DB=mysql    # TEST_MYSQL_HOST / _PORT / _USER / _PASSWORD / _NAME

The variables can be set in the environment or in ``.env`` at the project root
(see ``.env.example``). Variables already in the environment take precedence.
The server account needs to create and drop databases: pytest-django creates
``test_<NAME>`` (``test_<NAME>_<tox env>`` under tox), and every tenant in a
test gets its own ``test_tenant_*`` database.
"""

import os
import re
from pathlib import Path
from typing import Any

from django.core.exceptions import ImproperlyConfigured

PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKENDS = ("sqlite", "pg", "mysql")

_SERVERS = {
    "pg": ("TEST_PG", "django.db.backends.postgresql"),
    "mysql": ("TEST_MYSQL", "django.db.backends.mysql"),
}


def load_dotenv(path: Path = PROJECT_ROOT / ".env") -> None:
    """Copy ``KEY=VALUE`` lines from ``path`` into ``os.environ`` without overriding existing variables."""
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.removeprefix("export ").partition("=")
        key, value = key.strip(), value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        os.environ.setdefault(key, value)


def selected_backend() -> str:
    backend = os.environ.get("TEST_DB", "sqlite").strip().lower() or "sqlite"
    if backend not in BACKENDS:
        raise ImproperlyConfigured(f"TEST_DB={backend!r}: expected one of {', '.join(BACKENDS)}")
    return backend


def _require(name: str) -> str:
    try:
        return os.environ[name]
    except KeyError:
        raise ImproperlyConfigured(f"{name} is not set: add it to the environment or to .env") from None


def server_database(backend: str) -> dict[str, Any]:
    """``DATABASES["default"]`` for a server backend, read from ``TEST_<BACKEND>_*`` variables."""
    prefix, engine = _SERVERS[backend]
    cfg: dict[str, Any] = {
        "ENGINE": engine,
        "NAME": os.environ.get(f"{prefix}_NAME") or "django_db_tenants",
        "HOST": _require(f"{prefix}_HOST"),
        "PORT": _require(f"{prefix}_PORT"),
        "USER": _require(f"{prefix}_USER"),
        "PASSWORD": os.environ.get(f"{prefix}_PASSWORD", ""),
    }
    # One test database per tox env, so `tox -p` runs against the same server do not collide.
    suffix = re.sub(r"\W", "_", os.environ.get("TOX_ENV_NAME", ""))
    cfg["TEST"] = {"NAME": f"test_{cfg['NAME']}_{suffix}" if suffix else None}
    if backend == "mysql":
        cfg["OPTIONS"] = {"charset": "utf8mb4"}
        cfg["TEST"] |= {"CHARSET": "utf8mb4", "COLLATION": "utf8mb4_unicode_ci"}
    return cfg


def default_database(sqlite: dict[str, Any]) -> dict[str, Any]:
    """The "default" database for the selected backend. ``sqlite`` is used as is for ``TEST_DB=sqlite``."""
    load_dotenv()
    backend = selected_backend()
    return sqlite if backend == "sqlite" else server_database(backend)
