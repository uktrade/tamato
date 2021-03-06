# Generated by Django 3.1 on 2020-12-27 10:53
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
            name="TestModel1",
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
                ("valid_between", common.fields.TaricDateTimeRangeField()),
                ("sid", models.PositiveIntegerField()),
                ("name", models.CharField(max_length=24, null=True)),
            ],
            options={
                "abstract": False,
                "base_manager_name": "objects",
            },
            bases=("common.trackedmodel", models.Model),
        ),
        migrations.CreateModel(
            name="TestModel2",
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
                ("valid_between", common.fields.TaricDateTimeRangeField()),
                ("custom_sid", models.PositiveIntegerField()),
                ("description", models.CharField(max_length=24, null=True)),
            ],
            options={
                "abstract": False,
                "base_manager_name": "objects",
            },
            bases=("common.trackedmodel", models.Model),
        ),
        migrations.CreateModel(
            name="TestModel3",
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
                ("valid_between", common.fields.TaricDateTimeRangeField()),
                ("sid", models.PositiveIntegerField()),
                (
                    "linked_model",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to="tests.testmodel1",
                    ),
                ),
            ],
            options={
                "abstract": False,
                "base_manager_name": "objects",
            },
            bases=("common.trackedmodel", models.Model),
        ),
    ]
