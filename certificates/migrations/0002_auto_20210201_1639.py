# Generated by Django 3.1 on 2021-02-01 16:39
from django.db import migrations

from common.migration_operations import ConvertTaricDateRange


class Migration(migrations.Migration):
    dependencies = [
        ("certificates", "0001_initial"),
    ]

    operations = [
        ConvertTaricDateRange("certificate", "valid_between"),
        ConvertTaricDateRange("certificatedescription", "valid_between"),
        ConvertTaricDateRange("certificatetype", "valid_between"),
    ]