import contextlib
import json

from django import forms
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models

from . import crypto


class EncryptedTextField(models.TextField):
    """TextField whose value is Fernet-encrypted at rest.

    Transparent to application code: you read and write plain strings.
    Not searchable / not indexable by design.
    """

    description = "Encrypted text"

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value in (None, ""):
            return value
        return crypto.encrypt(str(value))

    def from_db_value(self, value, expression, connection):
        if value in (None, ""):
            return value
        try:
            return crypto.decrypt(value)
        except crypto.InvalidToken:
            # Value was written before encryption was enabled, or the key changed.
            # Returning it raw makes migrations to encryption painless; a wrong
            # key simply yields garbage credentials rather than a 500.
            return value


class EncryptedJSONField(models.TextField):
    """A JSON value (usually a dict) stored as Fernet-encrypted text.

    Transparent to application code: you read and write Python objects. Not
    searchable / not indexable / no JSON lookups, by design.
    """

    description = "Encrypted JSON"

    def get_prep_value(self, value):
        if value is None:
            return None
        return crypto.encrypt(json.dumps(value, cls=DjangoJSONEncoder))

    def from_db_value(self, value, expression, connection):
        if value in (None, ""):
            return None if value is None else {}
        with contextlib.suppress(crypto.InvalidToken):  # plain JSON written before encryption
            value = crypto.decrypt(value)
        try:
            return json.loads(value)
        except ValueError:
            # Wrong key: return the stored text so the row still loads (admin, lists);
            # code that needs the value fails on this client only.
            return value

    def to_python(self, value):
        if isinstance(value, str):
            try:
                return json.loads(value)
            except ValueError:
                return value
        return value

    def value_to_string(self, obj):
        return json.dumps(self.value_from_object(obj), cls=DjangoJSONEncoder)

    def formfield(self, **kwargs):
        kwargs.setdefault("form_class", forms.JSONField)
        kwargs.setdefault("encoder", DjangoJSONEncoder)
        return super().formfield(**kwargs)
