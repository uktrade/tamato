# Generated by Django 3.1.14 on 2022-11-30 14:27

import django.db.models.deletion
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    dependencies = [
        ("quotas", "0006_auto_20211218_1900"),
    ]

    operations = [
        migrations.AlterField(
            model_name="quotadefinition",
            name="order_number",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="definitions",
                to="quotas.quotaordernumber",
            ),
        ),
    ]