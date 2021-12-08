import logging
from importlib import import_module

from django.apps import AppConfig

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

    def ready(self):
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
