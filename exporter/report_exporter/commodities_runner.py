import csv
import logging
from tempfile import NamedTemporaryFile

from open_data.models import ReportGoodsNomenclature

logger = logging.getLogger(__name__)


def normalise_loglevel(loglevel):
    """
    Attempt conversion of `loglevel` from a string integer value (e.g. "20") to
    its loglevel name (e.g. "INFO").

    This function can be used after, for instance, copying log levels from
    environment variables, when the incorrect representation (int as string
    rather than the log level name) may occur.
    """
    try:
        return logging._levelToName.get(int(loglevel))
    except:
        return loglevel


class CommodityCodeExport:
    """Runs the export command against TAP data to extract commodity CSV
    data."""

    def __init__(self, target_file: NamedTemporaryFile):
        self.target_file = target_file

    #
    #
    #
    @staticmethod
    def csv_headers():
        """
        Produces a list of headers for the CSV.

        Returns:
            list: list of header names
        """
        commodity_code_headers = [
            "Id",
            "commodity__sid",
            "commodity__code",
            "commodity__suffix",
            "commodity__description",
            "commodity__validity_start",
            "commodity__validity_end",
            "parent__sid",
            "parent__code",
            "parent__suffix",
        ]

        return commodity_code_headers

    def run(self):
        """
        Produces data for the commodity export CSV, from the TAP database.

        Returns:
            None: Operations performed and stored within the NamedTemporaryFile
        """
        commodities = (
            ReportGoodsNomenclature.objects.all()
            .order_by("item_id", "suffix")
            .select_related("parent_trackedmodel_ptr")
            .prefetch_related("description")
        )

        id = 0
        with open(self.target_file.name, "wt") as file:
            writer = csv.writer(file)
            writer.writerow(self.csv_headers())
            for commodity in commodities:
                id += 1
                if commodity.parent_trackedmodel_ptr:
                    parent_sid = commodity.parent_trackedmodel_ptr.sid
                    parent_code = commodity.parent_trackedmodel_ptr.item_id
                    parent_suffix = commodity.parent_trackedmodel_ptr.suffix
                else:
                    parent_sid = ""
                    parent_code = ""
                    parent_suffix = ""

                commodity_data = [
                    id,
                    commodity.sid,
                    commodity.item_id,
                    commodity.suffix,
                    commodity.description.all().first().description,
                    commodity.valid_between.lower,
                    commodity.valid_between.upper,
                    parent_sid,
                    parent_code,
                    parent_suffix,
                ]

                writer.writerow(commodity_data)
