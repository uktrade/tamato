import csv
import logging
from tempfile import NamedTemporaryFile

from open_data.models import ReportMeasure

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


class MeasureExport:
    """Runs the export command against TAP data to extract Measure CSV data."""

    def __init__(self, target_file: NamedTemporaryFile):
        self.target_file = target_file

    @staticmethod
    def csv_headers():
        """
        Produces a list of headers for the CSV.

        Returns:
            list: list of header names
        """
        measure_headers = [
            "id",
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
            "measure__geographical_area__description",
            "measure__excluded_geographical_areas__ids",
            "measure__excluded_geographical_areas__descriptions",
            "measure__quota__order_number",
            "measure__regulation__id",
            "measure__regulation__url",
        ]

        return measure_headers

        def run(self):
            """
            Produces data for the commodity export CSV, from the TAP database.

            Returns:
                None: Operations performed and stored within the NamedTemporaryFile
            """
            measures = ReportMeasure.objects.filter(
                sid__gte=20000000,
            ).select_related("parent_trackedmodel_ptr")
            id = 0
            with open(self.target_file.name, "wt") as file:
                writer = csv.writer(file)
                writer.writerow(self.csv_headers())
                for measure in measures:
                    id += 1
                    if commodity.parent_trackedmodel_ptr:
                        parent_sid = commodity.parent_trackedmodel_ptr.sid
                        parent_code = commodity.parent_trackedmodel_ptr.item_id
                        parent_suffix = commodity.parent_trackedmodel_ptr.suffix
                    else:
                        parent_sid = ""
                        parent_code = ""
                        parent_suffix = ""

                    measure_data = [
                        id,
                        commodity.sid,
                        commodity.item_id,
                        commodity.suffix,
                        commodity.description,
                        commodity.valid_between.lower,
                        commodity.valid_between.upper,
                        parent_sid,
                        parent_code,
                        parent_suffix,
                    ]

                    writer.writerow(measure_data)

            query = """
SELECT T5."id", T5."polymorphic_ctype_id", T5."created_at", T5."updated_at", T5."transaction_id", T5."update_type", 
       T5."version_group_id", 
       "measures_measurecondition"."trackedmodel_ptr_id", 
       "measures_measurecondition"."sid", 
       "measures_measurecondition"."dependent_measure_id", 
       "measures_measurecondition"."condition_code_id", 
       "measures_measurecondition"."component_sequence_number", 
       "measures_measurecondition"."duty_amount", 
       "measures_measurecondition"."monetary_unit_id", 
       "measures_measurecondition"."condition_measurement_id", 
       "measures_measurecondition"."action_id", 
       "measures_measurecondition"."required_certificate_id", 
       MAX(T7."id") 
           FILTER 
               (WHERE (("common_transaction"."order" <= (20696121) AND "common_transaction"."partition" = (3) 
                            AND (("common_transaction"."partition" = 3 AND "common_transaction"."workbasket_id" = (1329)) 
                            OR "common_transaction"."partition" IN (1, 2))) OR "common_transaction"."partition" < (3))) AS "latest", 
    CASE WHEN "measures_measurecondition"."duty_amount" IS NULL THEN '' ELSE CONCAT(("measures_measurecondition"."duty_amount")::text, 
        (CONCAT((CASE WHEN ("measures_measurecondition"."duty_amount" IS NOT NULL AND "measures_measurecondition"."monetary_unit_id" IS NULL) 
            THEN '%' ELSE CONCAT(('')::text, ("measures_monetaryunit"."code")::text) END)::text, 
            (CONCAT((CASE WHEN ("measures_measurecondition"."condition_measurement_id" IS NULL 
                                    OR "measures_measurement"."measurement_unit_id" IS NULL OR "measures_measurementunit"."abbreviation" IS NULL) 
                THEN ' ' WHEN "measures_measurecondition"."monetary_unit_id" IS NULL 
                    THEN "measures_measurementunit"."abbreviation" ELSE CONCAT(( '/' )::text, 
                        ("measures_measurementunit"."abbreviation")::text) END)::text, 
                (CASE WHEN "measures_measurementunitqualifier"."abbreviation" IS NULL THEN '' ELSE CONCAT(( '/' )::text, 
                    ("measures_measurementunitqualifier"."abbreviation")::text) END)::text))::text))::text) END AS "reference_price_string" 

FROM "measures_measurecondition" INNER JOIN "measures_measure" 
    ON ("measures_measurecondition"."dependent_measure_id" = "measures_measure"."trackedmodel_ptr_id") 
    INNER JOIN "common_trackedmodel" ON ("measures_measure"."trackedmodel_ptr_id" = "common_trackedmodel"."id") 
    INNER JOIN "common_trackedmodel" T5 ON ("measures_measurecondition"."trackedmodel_ptr_id" = T5."id") 
    INNER JOIN "common_versiongroup" T6 ON (T5."version_group_id" = T6."id") LEFT OUTER JOIN "common_trackedmodel" T7 
        ON (T6."id" = T7."version_group_id") LEFT OUTER JOIN "common_transaction" 
            ON (T7."transaction_id" = "common_transaction"."id") 
    LEFT OUTER JOIN "measures_monetaryunit" ON ("measures_measurecondition"."monetary_unit_id" = "measures_monetaryunit"."trackedmodel_ptr_id") 
    LEFT OUTER JOIN "measures_measurement" ON ("measures_measurecondition"."condition_measurement_id" = "measures_measurement"."trackedmodel_ptr_id")
    LEFT OUTER JOIN "measures_measurementunit" ON ("measures_measurement"."measurement_unit_id" = "measures_measurementunit"."trackedmodel_ptr_id") 
    LEFT OUTER JOIN "measures_measurementunitqualifier" 
        ON ("measures_measurement"."measurement_unit_qualifier_id" = "measures_measurementunitqualifier"."trackedmodel_ptr_id") 
    INNER JOIN "measures_measureconditioncode" 
        ON ("measures_measurecondition"."condition_code_id" = "measures_measureconditioncode"."trackedmodel_ptr_id") 
WHERE ("common_trackedmodel"."version_group_id" = 9217766 AND NOT (T5."update_type" = 2)) 
GROUP BY T5."id", "measures_measurecondition"."trackedmodel_ptr_id", 19 
HAVING MAX(T7."id") FILTER (WHERE (("common_transaction"."order" <= (20696121) AND "common_transaction"."partition" = (3) AND (("common_transaction"."partition" = 3 AND "common_transaction"."workbasket_id" = (1329)) OR "common_transaction"."partition" IN (1, 2))) OR "common_transaction"."partition" < (3))) = ("measures_measurecondition"."trackedmodel_ptr_id")
"""
