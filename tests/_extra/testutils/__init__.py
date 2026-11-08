"""Shared test utilities for django-db-tenants.

``tests/_extra`` is on the pytest ``pythonpath``, so tests import from here::

    from testutils.factories import ClientFactory, UserFactory
    from testutils.tenants import reset_tenant_state

Fixtures are registered as a pytest plugin in ``tests/conftest.py``
(see :mod:`testutils.plugin`).
"""
