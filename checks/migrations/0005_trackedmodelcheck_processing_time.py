# Generated by Django 3.2.23 on 2023-11-21 10:06

from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    dependencies = [
        ("checks", "0004_auto_20220831_1621"),
    ]

    operations = [
        migrations.AddField(
            model_name="trackedmodelcheck",
            name="processing_time",
            field=models.DecimalField(decimal_places=4, max_digits=6, null=True),
        ),
    ]