# Generated by Django 4.2.16 on 2025-01-13 10:43

from django.db import migrations
from django.db import models


class Migration(migrations.Migration):

    dependencies = [
        ("common", "0012_user_sso_uuid"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="versiongroup",
            index=models.Index(
                fields=["current_version"],
                name="common_vers_current_04c358_idx",
            ),
        ),
    ]
