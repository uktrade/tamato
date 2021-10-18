import logging

import apsw

from common.app_config import CommonConfig

logger = logging.getLogger(__name__)

LEVELS = {
    apsw.SQLITE_OK: logging.INFO,
    apsw.SQLITE_WARNING: logging.WARNING,
}


def handle_sqlite_log(errcode, message):
    errstr = apsw.mapping_result_codes[errcode & 255]
    extended = errcode & ~255
    level = LEVELS.get(errcode & 255, logging.ERROR)
    logger.log(
        level,
        "%s (%d): %s",
        apsw.mapping_extended_result_codes.get(extended, errstr),
        errcode,
        message,
    )


class ExporterConfig(CommonConfig):
    name = "exporter"

    def ready(self):
        apsw.config(apsw.SQLITE_CONFIG_LOG, handle_sqlite_log)
