"""Map OIDC userinfo claims to a local user in the tenant database.

Replace via DB_TENANTS["SSO_USER_SYNC"] = "yourapp.sso.sync_user".
The callable receives (client, userinfo, request) and returns a user or None
(None = deny login).
"""

from typing import Any

from django.contrib.auth import get_user_model


def default_user_sync(client, userinfo: dict, request=None):
    # Any: works with custom user models, whose fields are probed with hasattr() below.
    User: Any = get_user_model()
    email = (userinfo.get("email") or "").strip().lower()
    if not email:
        return None

    username_field = User.USERNAME_FIELD
    lookup = {"email__iexact": email}
    user = User.objects.filter(**lookup).first()

    if user is None:
        if not client.oidc_auto_create_users:
            return None
        user = User(**{username_field: email})
        if username_field != "email" and hasattr(user, "email"):
            user.email = email
        user.set_unusable_password()

    if hasattr(user, "first_name"):
        user.first_name = userinfo.get("given_name") or user.first_name or ""
    if hasattr(user, "last_name"):
        user.last_name = userinfo.get("family_name") or user.last_name or ""
    if not user.is_active:
        return None
    user.save()
    return user
