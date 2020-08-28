import logging
from importlib import import_module

from django.apps import AppConfig


logger = logging.getLogger(__file__)


IMPORT_PARSER_NAME = "import_parsers"
IMPORT_HANDLER_NAME = "import_handlers"


class CommonConfig(AppConfig):
    def ready(self):
        modules_to_import = [
            f"{self.name}.{IMPORT_PARSER_NAME}",
            f"{self.name}.{IMPORT_HANDLER_NAME}",
        ]
        for module in modules_to_import:
            try:
                import_module(module)
            except ModuleNotFoundError:
                logger.debug(f"Failed to import {module}")
