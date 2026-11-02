from django.db import migrations


class Migration(migrations.Migration):
    """Drop the connection columns copied into Client.db_params by 0002."""

    dependencies = [
        ("django_db_tenants", "0002_db_strategy"),
    ]

    operations = [
        migrations.RemoveField(model_name="client", name="db_engine"),
        migrations.RemoveField(model_name="client", name="db_host"),
        migrations.RemoveField(model_name="client", name="db_options"),
        migrations.RemoveField(model_name="client", name="db_password"),
        migrations.RemoveField(model_name="client", name="db_port"),
        migrations.RemoveField(model_name="client", name="db_user"),
    ]
