# Generated by Django 3.2.23 on 2024-01-24 15:41

import django.db.models.deletion
from django.db import migrations
from django.db import models


def change_user_content_type(apps, schema_editor):
    """
    The addition of the new current_workbasket field marks the move to a custom
    user model from this point in migration history onwards.

    As a result, the auth.User content type must be updated to reflect
    common.User (custom user model) to preserve existing references.
    """

    ContentType = apps.get_model("contenttypes", "ContentType")
    ct = ContentType.objects.filter(
        app_label="auth",
        model="user",
    ).first()
    if ct:
        ct.app_label = "common"
        ct.save()


class Migration(migrations.Migration):
    dependencies = [
        ("workbaskets", "0008_datarow_dataupload"),
        ("common", "0007_auto_20221114_1040_fix_missing_current_versions"),
    ]

    operations = [
        migrations.RunPython(change_user_content_type),
        migrations.AddField(
            model_name="user",
            name="current_workbasket",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="workbaskets.workbasket",
            ),
        ),
    ]
