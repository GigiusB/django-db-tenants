from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from . import registry
from .db import unregister_db
from .models import Client, ClientDomain


@receiver(post_save, sender=Client)
def _client_saved(sender, instance, **kwargs):
    # Other processes notice the change when their cache entry expires; this
    # process re-registers immediately on the next request (config_version).
    registry.invalidate(instance)


@receiver(post_delete, sender=Client)
def _client_deleted(sender, instance, **kwargs):
    registry.invalidate(instance)
    unregister_db(instance.alias)


@receiver([post_save, post_delete], sender=ClientDomain)
def _domain_changed(sender, instance, **kwargs):
    registry.invalidate_host(instance.domain)
    registry.invalidate(instance.client)
