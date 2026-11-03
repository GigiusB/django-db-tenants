# Encryption

`Client.db_params` (the database strategy's parameters, including the database password) is stored encrypted with [Fernet](../../../glossary/#fernet). Code reads and writes plain values; the fields encrypt on the way in and decrypt on the way out.

Encryption covers the database columns only. The registry caches `Client` objects with these values decrypted; see [Known constraints](../../architecture/#known-constraints).

## The key

| `ENCRYPTION_KEY` | Key used |
|---|---|
| set (recommended) | that value: a url-safe base64 Fernet key (32 bytes) |
| `None` (default) | `urlsafe_b64encode(sha256(SECRET_KEY))` |

Generate a key:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

!!! warning "Set ENCRYPTION_KEY in production"
    Without it, rotating `SECRET_KEY` makes every stored secret unreadable.

The `Fernet` instance is built once per process (`get_fernet()` is cached). After changing the key at runtime, for example with `override_settings` in a test, call `crypto.get_fernet.cache_clear()`.

## EncryptedTextField

A `TextField` whose database value is a Fernet token. Empty strings and `None` are stored as they are. Not searchable or indexable: the same value encrypts differently each time.

When a stored value is not a valid token for the current key, reading it returns the raw stored value instead of failing. Plain-text values written before encryption was introduced therefore keep working (they are encrypted on the next save), but with a wrong key the field returns the encrypted token itself, and the connection or the IdP rejects it as a bad credential.

## EncryptedJSONField

A `TextField` holding a JSON value (usually a dict), stored as a Fernet token. Code reads and writes Python objects; the admin edits it as JSON text. No JSON lookups, ordering or indexing: the database only sees ciphertext.

| Stored value | Read as |
|---|---|
| a token for the current key | the decoded JSON value |
| plain JSON (written before encryption) | the decoded JSON value; encrypted on the next save |
| `NULL` / empty string | `None` / `{}` |
| anything else (for example a token for another key) | the stored text. The row still loads; the database strategy then raises `ImproperlyConfigured` for that client only |

Use them in your own models:

```python
from django_db_tenants.fields import EncryptedJSONField, EncryptedTextField


class Integration(models.Model):
    api_token = EncryptedTextField(blank=True)
    settings = EncryptedJSONField(default=dict, blank=True)
```

::: django_db_tenants.fields

::: django_db_tenants.crypto
