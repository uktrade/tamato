# Generated by Django 4.2.15 on 2024-11-26 13:55

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("tasks", "0014_remove_taskworkflow_description_and_more"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="taskworkflow",
            options={"verbose_name": "workflow"},
        ),
        migrations.AlterModelOptions(
            name="taskworkflowtemplate",
            options={"verbose_name": "workflow template"},
        ),
    ]