import logging
from datetime import date

logger = logging.getLogger(__name__)


class ReportExport:
    def __int__(self, prefix, export_fn):
        self.prefix = prefix
        self.export_fn = export_fn


def get_output_filename(prefix="export"):
    """
    Generate output filename with transaction order field.

    If no revisions are present the filename is prefixed with seed_.
    """
    date_str = f"{date.today().strftime('%Y%m%d')}"
    return f"{prefix}_{date_str}.csv"
