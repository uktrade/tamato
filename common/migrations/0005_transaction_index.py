# Generated by Django 3.1.14 on 2022-02-21 14:57

from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    dependencies = [
        ("common", "0004_transaction_partition_3_of_3"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="transaction",
            index=models.Index(
                fields=["partition", "order"],
                name="common_tran_partiti_2e4d30_idx",
            ),
        ),
    ]