# Generated by Django 3.1.12 on 2021-09-21 14:10

import django_fsm
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("workbaskets", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="workbasket",
            name="status",
            field=django_fsm.FSMField(
                choices=[
                    ("EDITING", "Editing"),
                    ("PROPOSED", "Proposed"),
                    ("APPROVED", "Approved"),
                    ("SENT", "Sent"),
                    ("PUBLISHED", "Published"),
                    ("ERRORED", "Errored"),
                ],
                db_index=True,
                default="EDITING",
                editable=False,
                max_length=50,
            ),
        ),
    ]