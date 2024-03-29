# Generated by Django 3.1 on 2021-02-01 16:39
from django.db import migrations

from common.migration_operations import ConvertTaricDateRange


class Migration(migrations.Migration):
    dependencies = [
        ("quotas", "0002_auto_20210114_1346"),
    ]

    operations = [
        ConvertTaricDateRange("quotablocking", "valid_between"),
        ConvertTaricDateRange("quotadefinition", "valid_between"),
        ConvertTaricDateRange("quotaordernumber", "valid_between"),
        ConvertTaricDateRange("quotaordernumberorigin", "valid_between"),
        ConvertTaricDateRange("quotasuspension", "valid_between"),
    ]
