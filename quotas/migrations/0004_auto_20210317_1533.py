# Generated by Django 3.1 on 2021-03-17 15:33

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("quotas", "0003_auto_20210201_1639"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="quotaordernumber",
            options={"verbose_name": "quota"},
        ),
    ]
