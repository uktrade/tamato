# Generated by Django 3.1 on 2021-01-06 15:33
import django.db.models.deletion
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="BatchDependencies",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="ImportBatch",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=32, unique=True)),
                ("split_job", models.BooleanField(default=False)),
                (
                    "dependencies",
                    models.ManyToManyField(
                        through="importer.BatchDependencies",
                        to="importer.ImportBatch",
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="ImporterXMLChunk",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "record_code",
                    models.CharField(blank=True, default=None, max_length=3, null=True),
                ),
                (
                    "chapter",
                    models.CharField(blank=True, default=None, max_length=2, null=True),
                ),
                ("chunk_number", models.PositiveSmallIntegerField()),
                ("chunk_text", models.TextField()),
                (
                    "status",
                    models.PositiveSmallIntegerField(
                        choices=[
                            (1, "WAITING"),
                            (2, "RUNNING"),
                            (3, "DONE"),
                            (4, "ERRORED"),
                        ],
                        default=1,
                    ),
                ),
                (
                    "batch",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="chunks",
                        to="importer.importbatch",
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.AddField(
            model_name="batchdependencies",
            name="dependent_batch",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="batch_dependencies",
                to="importer.importbatch",
            ),
        ),
        migrations.AddField(
            model_name="batchdependencies",
            name="depends_on",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="batch_dependents",
                to="importer.importbatch",
            ),
        ),
    ]