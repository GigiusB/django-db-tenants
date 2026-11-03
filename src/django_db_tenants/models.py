from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db import models
from strategy_field.fields import StrategyField

from . import strategies
from .conf import app_settings
from .fields import EncryptedJSONField

RESERVED_ALIASES = {"default"}


class Client(models.Model):
    """A tenant. Lives in the shared (template) database only.

    `slug` doubles as the Django database alias for the tenant's database.
    """

    class Status(models.TextChoices):
        PROVISIONING = "provisioning", "Provisioning"
        ACTIVE = "active", "Active"
        SUSPENDED = "suspended", "Suspended"

    name = models.CharField(max_length=200)
    slug = models.SlugField(
        max_length=63, unique=True, help_text="Used as the database alias. Immutable after creation."
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PROVISIONING)

    # --- Database (how to reach it is up to the strategy) ---------------------
    db_strategy = StrategyField(
        registry=strategies.registry,
        default=strategies.DEFAULT_STRATEGY,
        help_text="How the database is reached, created and dropped.",
    )
    db_name = models.CharField(max_length=200)
    db_params = EncryptedJSONField(
        default=dict,
        blank=True,
        help_text='Strategy parameters, encrypted at rest, e.g. {"HOST": "db2", "PASSWORD": "...", '
        '"OPTIONS": {"sslmode": "require"}}.',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.slug})"

    # ------------------------------------------------------------------------
    @property
    def alias(self) -> str:
        return self.slug

    @property
    def is_active(self) -> bool:
        return self.status == self.Status.ACTIVE

    def clean(self):
        if self.slug in RESERVED_ALIASES or self.slug == app_settings.TEMPLATE_ALIAS:
            raise ValidationError({"slug": f"'{self.slug}' is a reserved database alias."})
        if self.db_strategy is not None:  # an unknown strategy is reported by the field itself
            self.db_strategy.validate()

    def get_db_strategy(self) -> strategies.DatabaseStrategy:
        """The strategy instance bound to this client; raises when its class cannot be imported."""
        strategy = self.db_strategy
        if strategy is None:
            raw = self.__dict__.get("_strategy_fqn_db_strategy")
            raise ImproperlyConfigured(f"Client {self.slug!r}: database strategy {raw!r} cannot be imported")
        return strategy

    def config_version(self) -> str:
        """Changes whenever the row is saved; used to detect stale registrations."""
        return self.updated_at.isoformat() if self.updated_at else ""


class ClientDomain(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="domains")
    domain = models.CharField(max_length=253, unique=True, help_text="Host name without port, lower case.")
    is_primary = models.BooleanField(default=False)

    class Meta:
        ordering = ["-is_primary", "domain"]

    def __str__(self):
        return self.domain

    def save(self, *args, **kwargs):
        self.domain = self.domain.lower().strip()
        super().save(*args, **kwargs)
