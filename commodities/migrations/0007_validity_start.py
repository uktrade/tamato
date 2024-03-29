# Generated by Django 3.1.6 on 2021-04-20 17:04

from django.db import migrations
from django.db import models

from common import migration_operations


class Migration(migrations.Migration):
    dependencies = [
        ("commodities", "0006_auto_20210317_1153"),
    ]

    operations = [
        migrations.AddField(
            model_name="goodsnomenclatureindent",
            name="validity_start",
            field=models.DateField(blank=True, db_index=True, null=True),
        ),
        migrations.RunPython(
            migration_operations.copy_start_date_to_validity_start(
                "commodities",
                "goodsnomenclatureindent",
            ),
            migration_operations.copy_start_date_to_valid_between(
                "commodities",
                "goodsnomenclatureindent",
            ),
        ),
        migrations.AlterField(
            model_name="goodsnomenclatureindent",
            name="validity_start",
            field=models.DateField(blank=False, db_index=True, null=False),
        ),
        migrations.RemoveField(
            model_name="goodsnomenclatureindent",
            name="valid_between",
        ),
        migrations.AddField(
            model_name="goodsnomenclaturedescription",
            name="validity_start",
            field=models.DateField(blank=True, db_index=True, null=True),
        ),
        migrations.RunPython(
            migration_operations.copy_start_date_to_validity_start(
                "commodities",
                "goodsnomenclaturedescription",
            ),
            migration_operations.copy_start_date_to_valid_between(
                "commodities",
                "goodsnomenclaturedescription",
            ),
        ),
        migrations.AlterField(
            model_name="goodsnomenclaturedescription",
            name="validity_start",
            field=models.DateField(blank=False, db_index=True, null=False),
        ),
        migrations.AlterModelOptions(
            name="goodsnomenclaturedescription",
            options={"ordering": ("validity_start",)},
        ),
        migrations.RemoveField(
            model_name="goodsnomenclaturedescription",
            name="valid_between",
        ),
    ]
