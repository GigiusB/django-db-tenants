"""Move the tenant connection columns into the client's database strategy.

db_engine, db_host, db_port, db_user, db_password and db_options become keys of the
encrypted ``db_params`` object (ENGINE, HOST, PORT, USER, PASSWORD, OPTIONS), read by
the built-in ``TemplateOverlay`` strategy. Blank columns are left out, so they keep
inheriting the template connection, as before. 0003 drops the old columns: in a separate
migration (transaction) because PostgreSQL refuses ALTER TABLE after updating rows that
deferred foreign keys point at.
"""

import strategy_field.fields
from django.db import migrations

import django_db_tenants.fields

COLUMNS = {"db_engine": "ENGINE", "db_host": "HOST", "db_port": "PORT", "db_user": "USER", "db_password": "PASSWORD"}


def columns_to_params(apps, schema_editor):
    Client = apps.get_model("django_db_tenants", "Client")
    for client in Client.objects.using(schema_editor.connection.alias).all():
        params = {key: getattr(client, column) for column, key in COLUMNS.items() if getattr(client, column)}
        if client.db_options:
            params["OPTIONS"] = dict(client.db_options)
        client.db_params = params
        client.save(update_fields=["db_params"])


def params_to_columns(apps, schema_editor):
    Client = apps.get_model("django_db_tenants", "Client")
    for client in Client.objects.using(schema_editor.connection.alias).all():
        params = client.db_params if isinstance(client.db_params, dict) else {}
        for column, key in COLUMNS.items():
            setattr(client, column, str(params.get(key) or ""))
        client.db_options = params.get("OPTIONS") or {}
        client.save(update_fields=[*COLUMNS, "db_options"])


class Migration(migrations.Migration):
    dependencies = [
        ("django_db_tenants", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="client",
            name="db_strategy",
            field=strategy_field.fields.StrategyField(
                default="django_db_tenants.strategies.TemplateOverlay",
                help_text="How the database is reached, created and dropped.",
            ),
        ),
        migrations.AddField(
            model_name="client",
            name="db_params",
            field=django_db_tenants.fields.EncryptedJSONField(
                blank=True,
                default=dict,
                help_text='Strategy parameters, encrypted at rest, e.g. {"HOST": "db2", "PASSWORD": "...", '
                '"OPTIONS": {"sslmode": "require"}}.',
            ),
        ),
        migrations.RunPython(columns_to_params, params_to_columns),
    ]
