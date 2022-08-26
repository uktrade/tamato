# https://stackoverflow.com/a/53761784/62709
import sys
from pathlib import Path
from textwrap import dedent
from typing import Sequence

import black
from django.conf import settings
from django.core.management import BaseCommand
from django.core.management import CommandParser
from django.db import DEFAULT_DB_ALIAS
from django.db.migrations import Migration
from django.db.migrations.autodetector import MigrationAutodetector
from django.db.migrations.recorder import MigrationRecorder
from django.db.migrations.writer import MigrationWriter

from checks.models import BusinessRuleModel
from common.models.utils import ansi_hyperlink
from common.models.utils import is_database_synchronized


def _modify_migration_code(
    app_name: str,
    original_code: str,
    added_rules: Sequence[str],
    removed_rules: Sequence[str],
) -> str:
    """
    Modify the migration code to add the business rules.

    While another approach may be desirable, this is the one taken by other
    libraries that generate migrations, and allows explicitly embedding the
    business rules in the migration code.
    """
    header = "# Data Migration, written by sync_business_rules."

    extra_code = dedent(
        f"""\
        added_rules = {sorted(added_rules)}
        removed_rules = {sorted(removed_rules)}

        def add_rules(apps, schema_editor, rule_names):
            BusinessRuleModel = apps.get_model("{app_name}", "BusinessRuleModel")

            rules = [BusinessRuleModel(name=name) for name in rule_names]
            BusinessRuleModel.objects.bulk_create(rules)

        def mark_removed_rules(apps, schema_editor, rule_names):
            BusinessRuleModel = apps.get_model("{app_name}", "BusinessRuleModel")
            BusinessRuleModel.objects.filter(name__in=rule_names).update(current=False)

        def forward_sync_rules(apps, schema_editor):
            add_rules(apps, schema_editor, added_rules)
            mark_removed_rules(apps, schema_editor, removed_rules)

        def reverse_sync_rules(apps, schema_editor):
            '''
            Attempt to delete rules - developer may need to edit this to remove
            related models.
            '''
            BusinessRuleModel = apps.get_model("{app_name}", "BusinessRuleModel")
            BusinessRuleModel.objects.filter(name__in=added_rules).delete()
    """,
    )

    operations_code = "migrations.RunPython(forward_sync_rules, reverse_sync_rules)"

    # Now modify the code:
    code = header + "\n" + original_code
    code = code.replace("class Migration", f"{extra_code}\n\nclass Migration")

    code = code.replace(
        "operations = [",
        "operations = [\n" f"        {operations_code},",
    )

    return code


class Command(BaseCommand):
    """Override the write method to add more stuff before finishing."""

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--check",
            action="store_true",
            help="Check if migrations are pending.",
            default=False,
        )

    def write_sync_rules_migration(self, added_rules, removed_rules):
        """
        Generate a migration file that will sync the business rules in the
        database with those in the app.

        Works by generating an empty migration and adjusting the code, other libraries
        seem to take this approach - a nicer API to do this on Djangos side would
        be good.
        """
        app_name = "checks"

        # Get next migration number:
        prev_migration = (
            MigrationRecorder.Migration.objects.filter(app=app_name).last().name
        )
        prev_migration_number = MigrationAutodetector.parse_number(prev_migration)
        migration_number = f"{prev_migration_number + 1:04}"
        migration_name = f"{migration_number}_sync_business_rules"

        migration = Migration(migration_name, app_name)

        migration.dependencies = [(app_name, prev_migration)]
        writer = MigrationWriter(migration, include_header=True)

        writer_path = Path(writer.path)
        if writer_path.exists():
            sys.exit(f"Migration {migration_name} already exists.")

        writer_path.parent.mkdir(exist_ok=True)

        code = _modify_migration_code(
            app_name,
            writer.as_string(),
            added_rules,
            removed_rules,
        )
        formatted_code = black.format_str(code, mode=black.Mode())

        with open(writer.path, "w") as fp:
            fp.write(formatted_code)

        migration_path = Path(writer.path).relative_to(Path(settings.BASE_DIR))
        if self.stdout.isatty():
            migration_path = ansi_hyperlink(f"file://{writer.path}", migration_path)

        self.stdout.write(
            f"Wrote Business Rules updates "
            f"[Added: {len(added_rules)}, Removed: {len(removed_rules)}]:"
            f"  {migration_path}",
        )
        self.stdout.write("")
        self.stdout.write(
            "Please review the generated migration file to modify reverse migrations as necessary.",
        )
        self.stdout.write("")
        self.stdout.write("To apply the business rule updates, run the migration:")
        self.stdout.write(f"python manage.py migrate {app_name} {migration_number}")

    def handle(self, *app_labels, **options):
        # from checks.models import get_updated_rules

        added_rules, removed_rules = BusinessRuleModel.objects.get_updated_rules()
        business_rules_pending = added_rules or removed_rules

        migrations_pending = not is_database_synchronized(DEFAULT_DB_ALIAS)

        if options["check"]:
            self.stdout.write(
                "Migrations pending: " + ("Yes." if migrations_pending else "No."),
            )
            self.stdout.write(
                "Business models in sync: "
                + ("Yes." if not business_rules_pending else "No:"),
            )
            if added_rules or removed_rules:
                self.stdout.write(f" - Add: {len(added_rules)}")
                self.stdout.write(f" - Remove: {len(removed_rules)}")

            sys.exit(1)

        if migrations_pending:
            # Not only ensure schema migrations are up-to-date, but also ensure only
            # one business rule migration is written per update.
            sys.exit(
                "Run pending migrations before generating business rule migrations.",
            )

        if business_rules_pending:
            self.write_sync_rules_migration(added_rules, removed_rules)
        else:
            self.stdout.write(
                "Business rules are already synced, no migrations were created.",
            )
