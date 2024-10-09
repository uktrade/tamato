import csv
import logging
from tempfile import NamedTemporaryFile

from django.db import connection

from exporter.models.report_models import ExportMeasure

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


def refresh_materialized_views():
    with connection.cursor() as cursor:
        logger.info(f"Refreshing views")
        cursor.execute(
            "REFRESH MATERIALIZED VIEW  commodities_goodsnomenclatureindent__now ;",
        )
        cursor.execute(
            "REFRESH MATERIALIZED VIEW  commodities_goodsnomenclaturedescription__now ;",
        )
        cursor.execute(
            "REFRESH MATERIALIZED VIEW  geo_areas_geographicalareadescription__now ;",
        )
        cursor.execute("REFRESH MATERIALIZED VIEW  exclusions ;")
        cursor.execute("REFRESH MATERIALIZED VIEW  footnotes__expanded ;")
        cursor.execute("REFRESH MATERIALIZED VIEW  additional_codes__expanded ;")
        cursor.execute("REFRESH MATERIALIZED VIEW  conditions ;")
        cursor.execute("REFRESH MATERIALIZED VIEW  duty_sentences ;")
        cursor.execute("REFRESH MATERIALIZED VIEW  measures__now ;")
        cursor.execute("REFRESH MATERIALIZED VIEW  exporter_active_measures ;")
        logger.info(f"Completed refreshing views")


class measureExport:

    def __init__(self, target_file: NamedTemporaryFile):
        self.rows = []
        self.measures = None
        self.target_file = target_file

    @staticmethod
    def csv_headers():
        measure_headers = [
            "id",  # counter
            "trackedmodel_ptr_id",
            "commodity__sid",
            "commodity__code",
            "commodity__indent",
            "commodity__description",
            "measure__sid",
            "measure__type__id",
            "measure__type__description",
            "measure__additional_code__code",
            "measure__additional_code__description",
            "measure__duty_expression",
            "measure__effective_start_date",
            "measure__effective_end_date",
            "measure__reduction_indicator",
            "measure__footnotes",
            "measure__conditions",
            "measure__geographical_area__sid",
            "measure__geographical_area__id",
            "measure__geographical_area__description",  #
            "measure__excluded_geographical_areas__ids",  #
            "measure__excluded_geographical_areas__descriptions",  #
            "measure__quota__order_number",  #
            "measure__regulation__id",  #
            "measure__regulation__url",  #
        ]

        return measure_headers

    def run(self):
        refresh_materialized_views()

        measures_now = ExportMeasure.objects.order_by(
            "commodity_code",
            "measure_type_id",
            "measure_geographical_area_id",
        )

        counter = 1
        with open(self.target_file.name, "wt") as file:
            writer = csv.writer(file)
            writer.writerow(self.csv_headers())

            for measure in measures_now:
                measure_data = [
                    counter,
                    measure.trackedmodel_ptr_id,
                    measure.commodity_sid,
                    measure.commodity_code,
                    measure.commodity_indent,
                    measure.commodity_description,
                    measure.measure_sid,
                    measure.measure_type_id,
                    measure.measure_type_description,
                    measure.measure_additional_code_code,
                    measure.measure_additional_code_description,
                    measure.measure_duty_expression,
                    measure.measure_effective_start_date,
                    measure.measure_effective_end_date,
                    measure.measure_reduction_indicator,
                    measure.measure_footnotes,
                    measure.measure_conditions,
                    measure.measure_geographical_area_sid,
                    measure.measure_geographical_area_id,
                    measure.measure_geographical_area_description,
                    measure.measure_excluded_geographical_areas_ids,
                    measure.measure_excluded_geographical_areas_descriptions,
                    measure.measure_quota_order_number,
                    measure.measure_regulation_id,
                    measure.measure_regulation_url,
                ]

                writer.writerow(measure_data)
                counter += 1
