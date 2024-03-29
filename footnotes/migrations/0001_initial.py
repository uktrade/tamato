# Generated by Django 3.1 on 2021-01-06 15:33
import django.core.validators
import django.db.models.deletion
from django.db import migrations
from django.db import models

import common.fields


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("common", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Footnote",
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
                    "footnote_id",
                    models.CharField(
                        db_index=True,
                        max_length=5,
                        validators=[
                            django.core.validators.RegexValidator(
                                "^([0-9]{3}|[0-9]{5})$",
                            ),
                        ],
                    ),
                ),
            ],
            options={
                "ordering": ["footnote_type__footnote_type_id", "footnote_id"],
            },
            bases=("common.trackedmodel", models.Model),
        ),
        migrations.CreateModel(
            name="FootnoteType",
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
                    "footnote_type_id",
                    models.CharField(
                        db_index=True,
                        max_length=3,
                        validators=[
                            django.core.validators.RegexValidator(
                                "^[A-Z0-9]{2}[A-Z0-9 ]?$",
                            ),
                        ],
                    ),
                ),
                (
                    "application_code",
                    models.PositiveIntegerField(
                        choices=[
                            (1, "CN nomenclature"),
                            (2, "TARIC nomenclature"),
                            (3, "Export refund nomenclature"),
                            (4, "Wine reference nomenclature"),
                            (5, "Additional codes"),
                            (6, "CN measures"),
                            (7, "Other measures"),
                            (8, "Meursing Heading"),
                            (9, "Dynamic footnote"),
                        ],
                    ),
                ),
                ("description", common.fields.ShortDescription()),
            ],
            options={
                "abstract": False,
                "base_manager_name": "objects",
            },
            bases=("common.trackedmodel", models.Model),
        ),
        migrations.CreateModel(
            name="FootnoteDescription",
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
                ("description", models.TextField()),
                ("description_period_sid", common.fields.SignedIntSID()),
                (
                    "described_footnote",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="descriptions",
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
        migrations.AddField(
            model_name="footnote",
            name="footnote_type",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                to="footnotes.footnotetype",
            ),
        ),
    ]
