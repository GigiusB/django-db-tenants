"""pytest fixtures for django-db-tenants. Registered in ``tests/conftest.py``.

Fixtures
--------
``tenant_factory``
    ``tenant_factory("acme")`` -> an ACTIVE ``Client`` with a migrated database
    and the domain ``acme.test``.
``acme`` / ``globex``
    Two ready-made tenants.
``tenant_db_name``
    ``tenant_db_name("acme")`` -> a name for a new tenant database that is
    dropped when the test ends (the database itself is not created).
``tenant_template_db``
    Name of the session-wide migrated database that tenants are cloned from.

Tenant databases use the backend selected with ``TEST_DB`` (see
:mod:`testutils.databases` and :mod:`testutils.tenants`).

Every test starts and ends with :func:`testutils.tenants.reset_tenant_state`.

Django >= 6.1 test cases refuse connections to aliases that were not declared in
``TestCase.databases`` when the class was set up. Tenant aliases are registered
at runtime, after that point, so ``_allow_tenant_connections`` lets through
exactly the aliases created by ``ensure_db_registered`` and nothing else.
Tenant databases are not wrapped in the test transaction; isolation comes from
every test getting fresh tenant databases that are thrown away afterwards.
"""

from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any, Protocol

import pytest
from django.db.backends.base.base import BaseDatabaseWrapper

from django_db_tenants import db as tenants_db
from django_db_tenants.models import Client

from .factories import ClientDomainFactory, ClientFactory
from .tenants import (
    build_template_database,
    clone_database,
    create_empty_database,
    drop_database,
    new_database_name,
    reset_tenant_state,
)


class TenantFactory(Protocol):
    def __call__(
        self,
        slug: str | None = None,
        *,
        domains: list[str] | None = None,
        migrated: bool = True,
        **fields: Any,
    ) -> Client: ...


@pytest.fixture(autouse=True)
def _reset_tenant_state() -> Iterator[None]:
    reset_tenant_state()
    yield
    reset_tenant_state()


_DB_FIXTURES = {"db", "transactional_db", "django_db_reset_sequences", "django_db_serialized_rollback", "live_server"}


@pytest.fixture(autouse=True)
def _allow_tenant_connections(request: pytest.FixtureRequest) -> Iterator[None]:
    uses_db = request.node.get_closest_marker("django_db") is not None or bool(_DB_FIXTURES & set(request.fixturenames))
    if not uses_db:
        yield
        return
    with request.getfixturevalue("django_db_blocker").unblock():
        unguarded = BaseDatabaseWrapper.ensure_connection
    request.getfixturevalue("_django_db_helper")  # the test case (and its guard) must be set up first
    guarded = BaseDatabaseWrapper.ensure_connection

    def ensure_connection(self: BaseDatabaseWrapper) -> None:
        if self.alias in tenants_db._registered_versions:
            return unguarded(self)
        return guarded(self)

    BaseDatabaseWrapper.ensure_connection = ensure_connection
    try:
        yield
    finally:
        BaseDatabaseWrapper.ensure_connection = guarded


@pytest.fixture(scope="session")
def tenant_template_db(
    tmp_path_factory: pytest.TempPathFactory, django_db_blocker: Any, django_db_setup: None
) -> Iterator[str]:
    with django_db_blocker.unblock():
        name = new_database_name("template", tmp_path_factory.mktemp("tenant_template"))
        build_template_database(name)
    yield name
    with django_db_blocker.unblock():
        reset_tenant_state()
        drop_database(name)


@pytest.fixture
def tenant_db_name(tmp_path: Path, django_db_blocker: Any) -> Iterator[Callable[[str], str]]:
    created: list[str] = []

    def make(slug: str) -> str:
        name = new_database_name(slug, tmp_path)
        created.append(name)
        return name

    yield make
    with django_db_blocker.unblock():
        reset_tenant_state()  # close tenant connections, or the databases cannot be dropped
        for name in created:
            drop_database(name)


@pytest.fixture
def tenant_factory(db: None, tenant_db_name: Callable[[str], str], tenant_template_db: str) -> TenantFactory:
    def make(
        slug: str | None = None,
        *,
        domains: list[str] | None = None,
        migrated: bool = True,
        **fields: Any,
    ) -> Client:
        if slug is not None:
            fields["slug"] = slug
        client: Client = ClientFactory.build(**fields)
        client.db_name = tenant_db_name(client.slug)
        client.save()
        if migrated:
            clone_database(tenant_template_db, client)
        else:
            create_empty_database(client.db_name)
        for i, domain in enumerate(domains if domains is not None else [f"{client.slug}.test"]):
            ClientDomainFactory.create(client=client, domain=domain, is_primary=i == 0)
        return client

    return make


@pytest.fixture
def acme(tenant_factory: TenantFactory) -> Client:
    return tenant_factory("acme", name="ACME")


@pytest.fixture
def globex(tenant_factory: TenantFactory) -> Client:
    return tenant_factory("globex", name="Globex")
