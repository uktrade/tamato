# Generated by Django 4.2.16 on 2024-12-23 13:49

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("open_data", "0011_rename_duty_sentence_reportmeasure_reference_price"),
    ]

    operations = [
        migrations.RenameField(
            model_name="reportmeasure",
            old_name="reference_price",
            new_name="duty_sentence",
        ),
        migrations.RenameField(
            model_name="reportmeasurecondition",
            old_name="duty_sentence",
            new_name="reference_price",
        ),
    ]