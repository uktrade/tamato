# Generated by Django 3.1 on 2021-02-01 16:39

import django.core.validators
from django.db import migrations
from django.db import models

import common.fields


class Migration(migrations.Migration):
    dependencies = [
        ("regulations", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="regulation",
            name="information_text",
            field=common.fields.ShortDescription(
                validators=[
                    django.core.validators.RegexValidator(
                        "^[^|\\xA0]*$",
                        "Must not contain '|' or 0xA0",
                    ),
                ],
            ),
        ),
        migrations.AlterField(
            model_name="regulation",
            name="public_identifier",
            field=models.CharField(
                blank=True,
                help_text="This is the name of the regulation as it would appear on (for example) legislation.gov.uk",
                max_length=50,
                null=True,
                validators=[
                    django.core.validators.RegexValidator(
                        "^[^|\\xA0]*$",
                        "Must not contain '|' or 0xA0",
                    ),
                ],
            ),
        ),
        migrations.AlterField(
            model_name="regulation",
            name="url",
            field=models.URLField(
                blank=True,
                help_text="Please enter the absolute URL of the regulation",
                null=True,
                validators=[
                    django.core.validators.RegexValidator(
                        "^[^|\\xA0]*$",
                        "Must not contain '|' or 0xA0",
                    ),
                ],
            ),
        ),
    ]
