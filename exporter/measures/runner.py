import csv
import logging
from datetime import date
from tempfile import NamedTemporaryFile

from django.db.models import Q

from measures.models import Measure
from measures.models import MeasureType

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


class measureExport:

    def __init__(self, target_file: NamedTemporaryFile):
        self.rows = []
        self.measures = None
        self.target_file = target_file

    @staticmethod
    def csv_headers():
        measure_headers = [
            "id",  # counter
            "trackedmodel_ptr_id",  # trackedmodel_ptr_id
            "commodity__sid",  #
            "commodity__code",  #
            "commodity__indent",  #
            "commodity__description",  #
            "measure__sid",  # sid
            "measure__type__id",  #
            "measure__type__description",  #
            "measure__additional_code__code",  #
            "measure__additional_code__description",  #
            "measure__duty_expression",  #
            "measure__effective_start_date",  # lower(measures__now."valid_between")
            "measure__effective_end_date",  # upper(measures__now."valid_between")
            "measure__reduction_indicator",  # measures__now."reduction"
            "measure__footnotes",  #
            "measure__conditions",  #
            "measure__geographical_area__sid",  #
            "measure__geographical_area__id",  #
            "measure__geographical_area__description",  #
            "measure__excluded_geographical_areas__ids",  #
            "measure__excluded_geographical_areas__descriptions",  #
            "measure__quota__order_number",  #
            "measure__regulation__id",  #
            "measure__regulation__url",  #
        ]

        return measure_headers

    def run(self):
        filter_query = Q(valid_between__endswith__gte=date.today()) | Q(
            valid_between__endswith=None,
        )
        measures_now = (
            Measure.objects.latest_approved()
            .filter(
                filter_query,
                sid__gte=20000000,
            )
            .select_related("measure_type", "additional_code")
        )

        measure_type_now = MeasureType.objects.latest_approved()
        counter = 1

        with open(self.target_file.name, "wt") as file:
            writer = csv.writer(file)
            writer.writerow(self.csv_headers())

            for measure in measures_now:
                if counter % 10000 == 0:
                    print(counter)
                type_sid = measure.measure_type.sid

                measure_data = [
                    counter,  # counter
                    measure.trackedmodel_ptr_id,
                    "commodity__sid",  #
                    "commodity__code",  #
                    "commodity__indent",  #
                    "commodity__description",  #
                    measure.sid,  # sid
                    type_sid,
                    measure_type_now.get(sid=type_sid).description,
                    "measure__additional_code__code",  # FK measure.additional_code
                    "measure__additional_code__description",  #
                    "measure__duty_expression",  #
                    measure.valid_between.lower,
                    measure.valid_between.upper,
                    measure.reduction,
                    "measure__footnotes",  # Many to many
                    "measure__conditions",  #
                    "measure__geographical_area__sid",  # measure.geographical_area
                    "measure__geographical_area__id",  #
                    "measure__geographical_area__description",  #
                    "measure__excluded_geographical_areas__ids",  #
                    "measure__excluded_geographical_areas__descriptions",  #
                    "measure__quota__order_number",  # FK
                    "measure__regulation__id",  # FK
                    "measure__regulation__url",  #
                ]

                writer.writerow(measure_data)
                counter += 1

    # @staticmethod
    # def get_geographical_areas_and_exclusions(measure):
    #     geographical_areas = []
    #     geographical_area_exclusions = []
    #
    #     # get all geographical areas that are / were / will be enabled on the end date of the measure
    #     for origin in (
    #         measureOrderNumberOrigin.objects.latest_approved()
    #         .filter(
    #             order_number__order_number=measure.order_number.order_number,
    #             valid_between__startswith__lte=measure.valid_between.upper,
    #         )
    #         .filter(
    #             Q(valid_between__endswith__gte=measure.valid_between.upper)
    #             | Q(valid_between__endswith=None),
    #         )
    #     ):
    #         geographical_areas.append(
    #             origin.geographical_area.descriptions.latest_approved()
    #             .last()
    #             .description,
    #         )
    #         for (
    #             exclusion
    #         ) in origin.measureordernumberoriginexclusion_set.latest_approved():
    #             geographical_area_exclusions.append(
    #                 f"{exclusion.excluded_geographical_area.descriptions.latest_approved().last().description} excluded from {origin.geographical_area.descriptions.latest_approved().last().description}",
    #             )
    #
    #     geographical_areas_str = "|".join(geographical_areas)
    #     geographical_area_exclusions_str = "|".join(geographical_area_exclusions)
    #
    #     return geographical_areas_str, geographical_area_exclusions_str
    #
    # @staticmethod
    # def get_monetary_unit(measure):
    #     monetary_unit = None
    #     if measure.monetary_unit:
    #         monetary_unit = (
    #             f"{measure.monetary_unit.description} ({measure.monetary_unit.code})"
    #         )
    #     return monetary_unit
    #
    # @staticmethod
    # def get_measurement_unit(measure):
    #     measurement_unit_description = f"{measure.measurement_unit.description}"
    #     if measure.measurement_unit.abbreviation != "":
    #         measurement_unit_description = (
    #             measurement_unit_description
    #             + f" ({measure.measurement_unit.abbreviation})"
    #         )
    #     return measurement_unit_description
    #
    # @staticmethod
    # def get_api_query_date(measure):
    #     api_query_dates = []
    #
    #     # collect possible query dates, but only for current and historical, not future
    #     if measure.valid_between.lower <= date.today():
    #         if measure.valid_between.upper:
    #             # when not infinity
    #             api_query_dates.append(measure.valid_between.upper)
    #         else:
    #             # when infinity
    #             api_query_dates.append(date.today())
    #
    #         tap_measures = measure.order_number.measure_set.latest_approved().filter(
    #             # has valid between with end date and today's date is within that range
    #             Q(
    #                 valid_between__startswith__lte=date.today(),
    #                 valid_between__endswith__gte=date.today(),
    #             )
    #             |
    #             # has an open-ended date range but started before today
    #             Q(
    #                 valid_between__startswith__lte=date.today(),
    #                 valid_between__endswith=None,
    #             ),
    #         )
    #
    #         for tap_measure in tap_measures:
    #             if tap_measure.valid_between.upper is None:
    #                 api_query_dates.append(date.today())
    #             else:
    #                 api_query_dates.append(tap_measure.valid_between.upper)
    #
    #         api_query_dates.sort()
    #     else:
    #         # no query dates for future measures
    #         api_query_dates = [None]
    #
    #     return api_query_dates[0]
    #
    # @staticmethod
    # def get_associated_measures(measure):
    #
    #     measures = (
    #         Measure.objects.latest_approved()
    #         .filter(
    #             order_number=measure.order_number,
    #             valid_between__startswith__lte=measure.valid_between.upper,
    #         )
    #         .filter(
    #             Q(
    #                 valid_between__endswith__gte=measure.valid_between.upper,
    #             )
    #             | Q(
    #                 valid_between__endswith=None,
    #             ),
    #         )
    #     )
    #
    #     return measures
    #
    # def get_goods_nomenclature_item_ids(self, measure):
    #     item_ids = []
    #     for measure in self.get_associated_measures(measure):
    #         item_ids.append(measure.goods_nomenclature.item_id)
    #
    #     return item_ids
    #
    # def get_goods_nomenclature_headings(self, item_ids):
    #
    #     heading_item_ids = []
    #     headings = []
    #
    #     for item_id in item_ids:
    #         heading_item_id = item_id[:4]
    #         if heading_item_id not in heading_item_ids:
    #             heading_and_desc = (
    #                 heading_item_id
    #                 + "-"
    #                 + self.get_goods_nomenclature_description(
    #                     heading_item_id + "000000",
    #                 )
    #             )
    #             headings.append(heading_and_desc)
    #             heading_item_ids.append(heading_item_id)
    #
    #     return "|".join(headings)
    #
    # @staticmethod
    # def get_goods_nomenclature_description(item_id):
    #     description = (
    #         GoodsNomenclatureDescription.objects.latest_approved()
    #         .filter(
    #             described_goods_nomenclature__item_id=item_id,
    #         )
    #         .order_by("-validity_start")
    #         .first()
    #     )
    #
    #     return description.description
