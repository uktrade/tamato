# Generated by Django 3.1.6 on 2021-02-19 09:55

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("footnotes", "0002_auto_20210201_1639"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="footnotedescription",
            options={"ordering": ("valid_between",)},
        ),
    ]
