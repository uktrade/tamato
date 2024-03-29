# Generated by Django 3.1 on 2021-01-06 15:33
import django.core.validators
import django.db.models.deletion
from django.db import migrations
from django.db import models

import common.fields


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("footnotes", "0001_initial"),
        ("common", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="AdditionalCode",
            fields=[
                (
                    "trackedmodel_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="common.trackedmodel",
                    ),
                ),
                ("valid_between", common.fields.TaricDateTimeRangeField(db_index=True)),
                ("sid", common.fields.SignedIntSID()),
                (
                    "code",
                    models.CharField(
                        max_length=3,
                        validators=[
                            django.core.validators.RegexValidator(
                                "^[A-Z0-9][A-Z0-9][A-Z0-9]$",
                            ),
                        ],
                    ),
                ),
            ],
            options={
                "abstract": False,
                "base_manager_name": "objects",
            },
            bases=("common.trackedmodel", models.Model),
        ),
        migrations.CreateModel(
            name="AdditionalCodeType",
            fields=[
                (
                    "trackedmodel_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="common.trackedmodel",
                    ),
                ),
                ("valid_between", common.fields.TaricDateTimeRangeField(db_index=True)),
                (
                    "sid",
                    models.CharField(
                        db_index=True,
                        max_length=1,
                        validators=[
                            django.core.validators.RegexValidator("^[A-Z0-9]$"),
                        ],
                    ),
                ),
                ("description", common.fields.ShortDescription()),
                (
                    "application_code",
                    models.PositiveSmallIntegerField(
                        choices=[
                            (0, "Export refund nomenclature"),
                            (1, "Additional codes"),
                            (3, "Meursing additional codes"),
                            (4, "Export refund for processed agricultural goods"),
                        ],
                    ),
                ),
            ],
            options={
                "abstract": False,
                "base_manager_name": "objects",
            },
            bases=("common.trackedmodel", models.Model),
        ),
        migrations.CreateModel(
            name="FootnoteAssociationAdditionalCode",
            fields=[
                (
                    "trackedmodel_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="common.trackedmodel",
                    ),
                ),
                ("valid_between", common.fields.TaricDateTimeRangeField(db_index=True)),
                (
                    "additional_code",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to="additional_codes.additionalcode",
                    ),
                ),
                (
                    "associated_footnote",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to="footnotes.footnote",
                    ),
                ),
            ],
            options={
                "abstract": False,
                "base_manager_name": "objects",
            },
            bases=("common.trackedmodel", models.Model),
        ),
        migrations.CreateModel(
            name="AdditionalCodeDescription",
            fields=[
                (
                    "trackedmodel_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="common.trackedmodel",
                    ),
                ),
                ("valid_between", common.fields.TaricDateTimeRangeField(db_index=True)),
                ("description_period_sid", common.fields.SignedIntSID()),
                ("description", models.TextField()),
                (
                    "described_additional_code",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="descriptions",
                        to="additional_codes.additionalcode",
                    ),
                ),
            ],
            options={
                "abstract": False,
                "base_manager_name": "objects",
            },
            bases=("common.trackedmodel", models.Model),
        ),
        migrations.AddField(
            model_name="additionalcode",
            name="type",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                to="additional_codes.additionalcodetype",
            ),
        ),
    ]
