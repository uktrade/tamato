import logging
from importlib import import_module

from django.apps import AppConfig


logger = logging.getLogger(__file__)


IMPORTER_NAME = "import_handlers"


class CommonConfig(AppConfig):
    def ready(self):
        importer_module_name = f"{self.name}.{IMPORTER_NAME}"
        try:
            import_module(importer_module_name)
        except ModuleNotFoundError:
            logger.debug(f"Failed to import {importer_module_name}")
