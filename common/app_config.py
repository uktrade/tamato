import logging
import os
import sys
from importlib import import_module

from django.apps import AppConfig
from django.db import DEFAULT_DB_ALIAS

logger = logging.getLogger(__file__)


IMPORT_PARSER_NAME = "import_parsers"
IMPORT_HANDLER_NAME = "import_handlers"


class CommonConfig(AppConfig):
    """
    Extends the default Django AppConfig to load importer parser and handler
    modules for the app.

    Each app that defines tariff component models may also provide parser and
    handler modules to be used by the importer when reading the TARIC XML that
    describes those models. This class encapsulates the loading of those
    modules, so that we do not have to write the same code in each app's
    AppConfig.ready method.
    """

    def load_importer_modules(self):
        """Load importer parser and handler modules, if they exist."""
        modules_to_import = [
            f"{self.name}.{IMPORT_PARSER_NAME}",
            f"{self.name}.{IMPORT_HANDLER_NAME}",
        ]
        for module in modules_to_import:
            try:
                import_module(module)
            except ModuleNotFoundError:
                logger.debug(f"Failed to import {module}")

    def warn_if_business_rules_changed(self):
        """
        Output a message if the business rules in app don't match those in the
        database.

        A data migration to sync the rules may be created using the sync_business_rules
        management command.

        :return:  True if the rules need syncing, or there are unapplied migrations to this app.
        """
        from checks.models import BusinessRuleModel
        from common.models.utils import is_database_synchronized

        if not is_database_synchronized(DEFAULT_DB_ALIAS):
            logger.debug(
                "Database has pending migrations, run them before checking if business rule sync is required.",
            )
            # There are unapplied migrations (some of which may be ones needed to run the business rules.)
            return True

        added, removed = BusinessRuleModel.objects.get_updated_rules()
        sync_required = bool(added or removed)
        if sync_required:
            print(
                f"Business rules are not synced to the database. (Added: {len(added)},  Removed: {len(removed)})",
                file=sys.stderr,
            )
            print(
                "Create a data migration to sync the rules using the management command:\n  "
                "sync_business_rules",
                file=sys.stderr,
            )

        return sync_required

    def ready(self):
        in_runserver = bool(os.environ.get("RUN_MAIN"))

        self.load_importer_modules()
        if in_runserver:
            if self.warn_if_business_rules_changed():
                sys.exit(1)
