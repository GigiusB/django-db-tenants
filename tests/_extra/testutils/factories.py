"""factory_boy factories.

Shared-app models (``Client``, ``ClientDomain``) always land in the shared
database. Tenant-app models (users, notes) go wherever the router sends them,
so create them inside ``tenant_context``::

    with tenant_context(acme):
        NoteFactory.create(author=UserFactory.create())

Factories are generic (``DjangoModelFactory[Client]``), so prefer the explicit
``.create()`` / ``.build()`` / ``.create_batch()`` calls: they are typed, while
calling the factory class directly is not.
"""

from typing import Any

import factory
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from factory.django import DjangoModelFactory, Password

from django_db_tenants.models import Client, ClientDomain
from notes.models import Note

DEFAULT_PASSWORD = "pw"
OIDC_STRATEGY = "django_db_tenants.oidc.OidcStrategy"


def sso_params(slug: str, **sso: Any) -> dict[str, Any]:
    """``db_params`` for ``OidcStrategy`` with a provider for client ``slug``; ``sso`` overrides its keys."""
    return {
        "SSO": {
            "ISSUER": f"https://idp.example.com/{slug}",
            "CLIENT_ID": f"{slug}-client",
            "CLIENT_SECRET": "oidc-secret",
            **sso,
        }
    }


class ClientFactory(DjangoModelFactory[Client]):
    """An ACTIVE client whose ``db_name`` is a placeholder.

    For a client with a real, migrated database use the ``tenant_factory`` fixture.
    """

    class Meta:
        model = Client
        django_get_or_create = ("slug",)
        skip_postgeneration_save = True

    name = factory.Faker("company")
    slug = factory.Sequence(lambda n: f"tenant{n}")
    status = Client.Status.ACTIVE
    db_name = factory.LazyAttribute(lambda o: f"tenant_{o.slug}")

    class Params:
        provisioning = factory.Trait(status=Client.Status.PROVISIONING)
        suspended = factory.Trait(status=Client.Status.SUSPENDED)
        sso = factory.Trait(db_strategy=OIDC_STRATEGY, db_params=factory.LazyAttribute(lambda o: sso_params(o.slug)))


class ClientDomainFactory(DjangoModelFactory[ClientDomain]):
    class Meta:
        model = ClientDomain
        django_get_or_create = ("domain",)

    client = factory.SubFactory(ClientFactory)
    domain = factory.LazyAttribute(lambda o: f"{o.client.slug}.test")
    is_primary = True


class UserFactory(DjangoModelFactory[AbstractUser]):
    class Meta:
        model = get_user_model()
        django_get_or_create = ("username",)
        skip_postgeneration_save = True

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda o: f"{o.username}@example.com")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    password = Password(DEFAULT_PASSWORD)
    is_active = True


class NoteFactory(DjangoModelFactory[Note]):
    class Meta:
        model = Note

    author = factory.SubFactory(UserFactory)
    title = factory.Faker("sentence", nb_words=4)
    body = factory.Faker("paragraph")
