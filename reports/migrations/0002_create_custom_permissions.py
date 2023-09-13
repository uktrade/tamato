from django.contrib.auth.models import Permission, Group
from django.contrib.contenttypes.models import ContentType
from reports.models import Report
from django.db import migrations


def create_custom_permissions(apps, schema_editor):
    content_type = ContentType.objects.get_for_model(Report)

    view_permission, _ = Permission.objects.get_or_create(
        codename="view_report_index",
        name="Can view report index",
        content_type=content_type,
    )

    edit_permission, _ = Permission.objects.get_or_create(
        codename="view_report",
        name="Can view reports",
        content_type=content_type,
    )


class Migration(migrations.Migration):
    dependencies = [
        ("reports", "0001_report"),
    ]

    operations = [
        migrations.RunPython(create_custom_permissions),
    ]
