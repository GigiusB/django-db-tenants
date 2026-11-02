import django.db.models.deletion
from django.db import migrations, models

import django_db_tenants.fields


class Migration(migrations.Migration):
    initial = True
    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Client",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=200)),
                (
                    "slug",
                    models.SlugField(
                        help_text="Used as the database alias. Immutable after creation.", max_length=63, unique=True
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[("provisioning", "Provisioning"), ("active", "Active"), ("suspended", "Suspended")],
                        default="provisioning",
                        max_length=20,
                    ),
                ),
                (
                    "db_engine",
                    models.CharField(blank=True, help_text="e.g. django.db.backends.postgresql", max_length=100),
                ),
                ("db_name", models.CharField(max_length=200)),
                ("db_host", models.CharField(blank=True, max_length=255)),
                ("db_port", models.CharField(blank=True, max_length=10)),
                ("db_user", models.CharField(blank=True, max_length=200)),
                ("db_password", django_db_tenants.fields.EncryptedTextField(blank=True)),
                (
                    "db_options",
                    models.JSONField(
                        blank=True, default=dict, help_text="Merged into the OPTIONS dict (e.g. sslmode)."
                    ),
                ),
                ("sso_enabled", models.BooleanField(default=False)),
                (
                    "oidc_issuer",
                    models.URLField(blank=True, help_text="Issuer URL; /.well-known/openid-configuration is appended."),
                ),
                ("oidc_client_id", models.CharField(blank=True, max_length=255)),
                ("oidc_client_secret", django_db_tenants.fields.EncryptedTextField(blank=True)),
                ("oidc_scopes", models.CharField(default="openid email profile", max_length=255)),
                (
                    "oidc_auto_create_users",
                    models.BooleanField(default=True, help_text="Create a local user on first SSO login."),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="ClientDomain",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "domain",
                    models.CharField(help_text="Host name without port, lower case.", max_length=253, unique=True),
                ),
                ("is_primary", models.BooleanField(default=False)),
                (
                    "client",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="domains",
                        to="django_db_tenants.client",
                    ),
                ),
            ],
            options={"ordering": ["-is_primary", "domain"]},
        ),
    ]
