"""A plain Django app. Nothing tenant-specific here: the router sends these
tables to whichever tenant database is active.

Note the FK to the user model, which lives in the *same* tenant database. Never
add a ForeignKey to ``django_db_tenants.Client`` from a tenant app: Django cannot
follow relations across databases. Store ``client.slug`` instead if you need it.
"""

from django.conf import settings
from django.db import models


class Note(models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notes")
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title
