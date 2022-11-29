from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("measures", "0010_add_requires_to_action_and_accepts_to_condition_code"),
        ("common", "0006_auto_20221114_1000"),
        ("workbaskets", "0005_workbasket_rule_check_task_id"),
        ("geo_areas", "0005_rename_described_area"),
    ]

    operations = []
