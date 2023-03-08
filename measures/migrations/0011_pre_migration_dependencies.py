from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("contenttypes", "0001_initial"),
        ("footnotes", "0006_allow_blank_descriptions"),
        ("contenttypes", "0002_remove_content_type_name"),
        ("measures", "0010_add_requires_to_action_and_accepts_to_condition_code"),
        ("commodities", "0010_delete_goodsnomenclatureindentnode"),
        ("geo_areas", "0005_rename_described_area"),
        ("workbaskets", "0005_workbasket_rule_check_task_id"),
    ]

    operations = []
