# Generated by Django 3.1.6 on 2021-04-20 17:04

from django.db import migrations
from django.db import models

from common import migration_operations


class Migration(migrations.Migration):
    dependencies = [
        ("geo_areas", "0003_auto_20210219_0953"),
    ]

    operations = [
        migrations.AddField(
            model_name="geographicalareadescription",
            name="validity_start",
            field=models.DateField(blank=True, db_index=True, null=True),
        ),
        migrations.AlterModelOptions(
            name="geographicalareadescription",
            options={"ordering": ("validity_start",)},
        ),
        migrations.RunPython(
            migration_operations.copy_start_date_to_validity_start(
                "geo_areas",
                "geographicalareadescription",
            ),
            migration_operations.copy_start_date_to_valid_between(
                "geo_areas",
                "geographicalareadescription",
            ),
        ),
        migrations.RemoveField(
            model_name="geographicalareadescription",
            name="valid_between",
        ),
        migrations.AlterField(
            model_name="geographicalareadescription",
            name="validity_start",
            field=models.DateField(blank=False, db_index=True, null=False),
        ),
    ]