# Generated by Django 3.2.19 on 2023-06-28 08:05

import django_chunk_upload_handlers.clam_av
from django.db import migrations
from django.db import models

import importer.storages


class Migration(migrations.Migration):
    dependencies = [
        ("importer", "0007_importbatch_workbasket"),
    ]

    operations = [
        migrations.AddField(
            model_name="importbatch",
            name="taric_file",
            field=models.FileField(
                default="",
                blank=True,
                storage=importer.storages.CommodityImporterStorage,
                upload_to="",
                validators=[
                    django_chunk_upload_handlers.clam_av.validate_virus_check_result,
                ],
            ),
        ),
    ]