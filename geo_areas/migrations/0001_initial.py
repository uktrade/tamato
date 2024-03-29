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
            name="GeographicalArea",
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
                    "area_id",
                    models.CharField(
                        max_length=4,
                        validators=[
                            django.core.validators.RegexValidator(
                                "^[A-Z0-9]{2}$|^[A-Z0-9]{4}$",
                            ),
                        ],
                    ),
                ),
                (
                    "area_code",
                    models.PositiveSmallIntegerField(
                        choices=[
                            (0, "Country"),
                            (1, "Geographical Area Group"),
                            (2, "Region"),
                        ],
                    ),
                ),
            ],
            bases=("common.trackedmodel", models.Model),
        ),
        migrations.CreateModel(
            name="GeographicalMembership",
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
                    "geo_group",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="members",
                        to="geo_areas.geographicalarea",
                    ),
                ),
                (
                    "member",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="groups",
                        to="geo_areas.geographicalarea",
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
            name="GeographicalAreaDescription",
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
                ("description", common.fields.ShortDescription()),
                ("sid", common.fields.SignedIntSID()),
                (
                    "area",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="descriptions",
                        to="geo_areas.geographicalarea",
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
            model_name="geographicalarea",
            name="memberships",
            field=models.ManyToManyField(
                related_name="_geographicalarea_memberships_+",
                through="geo_areas.GeographicalMembership",
                to="geo_areas.GeographicalArea",
            ),
        ),
        migrations.AddField(
            model_name="geographicalarea",
            name="parent",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to="geo_areas.geographicalarea",
            ),
        ),
        migrations.AddConstraint(
            model_name="geographicalarea",
            constraint=models.CheckConstraint(
                check=models.Q(
                    ("area_code", 1),
                    ("parent__isnull", True),
                    _connector="OR",
                ),
                name="only_groups_have_parents",
            ),
        ),
    ]
