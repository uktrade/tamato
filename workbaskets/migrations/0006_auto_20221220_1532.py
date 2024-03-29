# Generated by Django 3.1.14 on 2022-12-20 15:32

import django_fsm
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("workbaskets", "0005_workbasket_rule_check_task_id"),
    ]

    operations = [
        migrations.AlterField(
            model_name="workbasket",
            name="status",
            field=django_fsm.FSMField(
                choices=[
                    ("ARCHIVED", "Archived"),
                    ("EDITING", "Editing"),
                    ("QUEUED", "Queued"),
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
