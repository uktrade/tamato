from collections import defaultdict

from django.core.management import BaseCommand

from checks.models import BusinessRuleModel
from common.business_rules import ALL_RULES


class Command(BaseCommand):
    """Display the business rules in the system and database."""

    def handle(self, *app_labels, **options):
        self.stdout.write("Rule Name,  In System,  In Database,  Status")

        # Create a dictionary of rule_names, then a couple of flags
        # to determine status.
        rule_info = defaultdict(dict)
        for rule_name in BusinessRuleModel.objects.values("name"):
            rule_info[rule_name["name"]]["in_database"] = True

        for rule_name in ALL_RULES.keys():
            rule_info[rule_name]["in_system"] = True

        for rule_name, info in rule_info.items():
            in_database = info.get("in_database", False)
            in_system = info.get("in_system", False)

            if in_database and in_system:
                status = "In Sync"
            elif in_database:
                status = "Pending Removal"
            elif in_system:
                status = "Pending Addition"

            self.stdout.write(
                f"{rule_name},"
                f" {'Y' if in_system else 'N'},"
                f" {'Y' if in_database else 'N'},"
                f" {status}",
            )
