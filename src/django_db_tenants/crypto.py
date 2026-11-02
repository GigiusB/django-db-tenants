import base64
import hashlib
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings

from .conf import app_settings


@lru_cache(maxsize=1)
def get_fernet() -> Fernet:
    key = app_settings.ENCRYPTION_KEY
    if not key:
        # Derive a stable 32-byte key from SECRET_KEY. Prefer an explicit key.
        digest = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
        key = base64.urlsafe_b64encode(digest)
    if isinstance(key, str):
        key = key.encode()
    return Fernet(key)


def encrypt(value: str) -> str:
    return get_fernet().encrypt(value.encode()).decode()


def decrypt(token: str) -> str:
    return get_fernet().decrypt(token.encode()).decode()


__all__ = ["InvalidToken", "decrypt", "encrypt", "get_fernet"]
