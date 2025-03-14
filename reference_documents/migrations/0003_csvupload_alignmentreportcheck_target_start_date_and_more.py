# Generated by Django 4.2.15 on 2024-12-19 14:51

import datetime

import django.db.models.deletion
import django_fsm
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):

    dependencies = [
        (
            "reference_documents",
            "0002_alignmentreport_alignmentreportcheck_refordernumber_and_more",
        ),
    ]

    operations = [
        migrations.CreateModel(
            name="CSVUpload",
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
                    "status",
                    django_fsm.FSMField(
                        choices=[
                            ("PENDING", "Pending"),
                            ("PROCESSING", "Processing"),
                            ("COMPLETE", "Complete"),
                            ("ERRORED", "Errored"),
                        ],
                        db_index=True,
                        default="PENDING",
                        editable=False,
                        max_length=50,
                    ),
                ),
                (
                    "preferential_rates_csv_data",
                    models.TextField(blank=True, null=True),
                ),
                ("order_number_csv_data", models.TextField(blank=True, null=True)),
                ("quota_definition_csv_data", models.TextField(blank=True, null=True)),
                ("error_details", models.TextField(blank=True, null=True)),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.AddField(
            model_name="alignmentreportcheck",
            name="target_start_date",
            field=models.DateTimeField(default=datetime.date(2024, 1, 1)),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="alignmentreportcheck",
            name="ref_order_number",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="ref_order_number_checks",
                to="reference_documents.refordernumber",
            ),
        ),
        migrations.AlterField(
            model_name="alignmentreportcheck",
            name="ref_quota_definition",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="ref_quota_definition_checks",
                to="reference_documents.refquotadefinition",
            ),
        ),
        migrations.AlterField(
            model_name="alignmentreportcheck",
            name="ref_quota_definition_range",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="ref_quota_definition_range_checks",
                to="reference_documents.refquotadefinitionrange",
            ),
        ),
        migrations.AlterField(
            model_name="alignmentreportcheck",
            name="ref_quota_suspension",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="ref_quota_suspension_checks",
                to="reference_documents.refquotasuspension",
            ),
        ),
        migrations.AlterField(
            model_name="alignmentreportcheck",
            name="ref_quota_suspension_range",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="ref_quota_suspension_range_checks",
                to="reference_documents.refquotasuspensionrange",
            ),
        ),
        migrations.AlterField(
            model_name="alignmentreportcheck",
            name="ref_rate",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="ref_rate_checks",
                to="reference_documents.refrate",
            ),
        ),
        migrations.AlterField(
            model_name="refordernumber",
            name="relation_type",
            field=models.CharField(
                blank=True,
                choices=[
                    ("EQ", "Equivalent to main quota"),
                    ("NM", "Normal (restrictive to main quota)"),
                ],
                max_length=2,
                null=True,
            ),
        ),
    ]
