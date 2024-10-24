import csv
import logging
from datetime import date
from datetime import timedelta
from tempfile import NamedTemporaryFile
from typing import List

from django.db.models import Q

from commodities.models import GoodsNomenclatureDescription
from measures.models import Measure
from quotas.models import QuotaDefinition
from quotas.models import QuotaOrderNumberOrigin

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


class QuotaExport:
    """
    Runs the export command against TAP data to extract quota CSV data
    """

    def __init__(self, target_file: NamedTemporaryFile):
        # self.rows = []
        # self.quotas = None
        self.target_file = target_file

    @staticmethod
    def csv_headers():
        """
        produces a list of headers for the CSV

        Returns:
            list: list of header names

        """
        quota_headers = [
            "quota_definition__sid",
            "quota__order_number",
            "quota__geographical_areas",
            "quota__geographical_area_exclusions",
            "quota__headings",
            "quota__commodities",
            "quota__measurement_unit",
            "quota__monetary_unit",
            "quota_definition__description",
            "quota_definition__validity_start_date",
            "quota_definition__validity_end_date",
            # 'quota_definition__suspension_periods', from HMRC data
            # 'quota_definition__blocking_periods', from HMRC data
            # 'quota_definition__status', from HMRC data
            # 'quota_definition__last_allocation_date', from HMRC data
            "quota_definition__initial_volume",
            # 'quota_definition__balance', from HMRC data
            # 'quota_definition__fill_rate', from HMRC data
            "api_query_date",  #  used to query the HMRC API
        ]

        return quota_headers

    def run(self):
        """
        produces data for the quota export CSV, from the TAP database.

        Returns:
            None: Operations performed and stored within the NamedTemporaryFile

        """

        quotas = QuotaDefinition.objects.latest_approved().filter(
            sid__gte=20000,
            valid_between__startswith__lte=date.today() + timedelta(weeks=52 * 3),
        )

        with open(self.target_file.name, "wt") as file:
            writer = csv.writer(file)
            writer.writerow(self.csv_headers())
            for quota in quotas:
                item_ids = self.get_goods_nomenclature_item_ids(quota)
                geographical_areas, geographical_area_exclusions = (
                    self.get_geographical_areas_and_exclusions(quota)
                )
                goods_nomenclature_headings = self.get_goods_nomenclature_headings(
                    item_ids,
                )
                if geographical_areas != "" and goods_nomenclature_headings != "":
                    quota_data = [
                        quota.sid,
                        quota.order_number.order_number,
                        geographical_areas,
                        geographical_area_exclusions,
                        goods_nomenclature_headings,
                        "|".join(item_ids),
                        self.get_measurement_unit(quota),
                        self.get_monetary_unit(quota),
                        quota.description,
                        quota.valid_between.lower,
                        quota.valid_between.upper,
                        quota.initial_volume,
                        self.get_api_query_date(quota),
                    ]

                    writer.writerow(quota_data)

    @staticmethod
    def get_geographical_areas_and_exclusions(quota):
        """
        returns a tuple of geographical areas and exclusions associated with a Quota

        Args:
            quota: the quota to be queried

        Returns:
            tuple(str, str) : geographical areas and exclusions
        """
        geographical_areas = []
        geographical_area_exclusions = []

        # get all geographical areas that are / were / will be enabled on the end date of the quota
        for origin in (
            QuotaOrderNumberOrigin.objects.latest_approved()
            .filter(
                order_number__order_number=quota.order_number.order_number,
                valid_between__startswith__lte=quota.valid_between.upper,
            )
            .filter(
                Q(valid_between__endswith__gte=quota.valid_between.upper)
                | Q(valid_between__endswith=None),
            )
        ):
            geographical_areas.append(
                origin.geographical_area.descriptions.latest_approved()
                .last()
                .description,
            )
            for (
                exclusion
            ) in origin.quotaordernumberoriginexclusion_set.latest_approved():
                geographical_area_exclusions.append(
                    f"{exclusion.excluded_geographical_area.descriptions.latest_approved().last().description} excluded from {origin.geographical_area.descriptions.latest_approved().last().description}",
                )

        geographical_areas_str = "|".join(geographical_areas)
        geographical_area_exclusions_str = "|".join(geographical_area_exclusions)

        return geographical_areas_str, geographical_area_exclusions_str

    @staticmethod
    def get_monetary_unit(quota):
        """
        returns the monetary unit associated with a Quota as a string

        Args:
            quota: the quota to be queried

        Returns:
            str or None: Monetary unit as string or None

        """
        monetary_unit = None
        if quota.monetary_unit:
            monetary_unit = (
                f"{quota.monetary_unit.description} ({quota.monetary_unit.code})"
            )
        return monetary_unit

    @staticmethod
    def get_measurement_unit(quota):
        """
        returns the measurement unit associated with a Quota as a string

        Args:
            quota: the quota to be queried

        Returns:
            str or None: Measurement unit as string or None

        """
        if quota.measurement_unit:
            measurement_unit_description = f"{quota.measurement_unit.description}"
            if quota.measurement_unit.abbreviation != "":
                measurement_unit_description = (
                    measurement_unit_description
                    + f" ({quota.measurement_unit.abbreviation})"
                )
            return measurement_unit_description
        return None

    @staticmethod
    def get_api_query_date(quota):
        """
        returns the most appropriate date for querying the HMRC API

        Dates are checked against current date and collected, the oldest of
        the dates is used as the API query date. Typically, this wil be today's date
        or the end date of the quota if < today's date

        note: quotas that start in the future will not be populated on the HMRC API so
        None s returned to indicate this query can be safely skipped

        Args:
            quota: The quota to be queried

        Returns:
            date or none: a date if available or none if quota is in the future

        """
        api_query_dates = []

        # collect possible query dates, but only for current and historical, not future
        if quota.valid_between.lower <= date.today():
            if quota.valid_between.upper:
                # when not infinity
                api_query_dates.append(quota.valid_between.upper)
            else:
                # when infinity
                api_query_dates.append(date.today())

            tap_measures = quota.order_number.measure_set.latest_approved().filter(
                # has valid between with end date and today's date is within that range
                Q(
                    valid_between__startswith__lte=date.today(),
                    valid_between__endswith__gte=date.today(),
                )
                |
                # has an open-ended date range but started before today
                Q(
                    valid_between__startswith__lte=date.today(),
                    valid_between__endswith=None,
                ),
            )

            for tap_measure in tap_measures:
                if tap_measure.valid_between.upper is None:
                    api_query_dates.append(date.today())
                else:
                    api_query_dates.append(tap_measure.valid_between.upper)

            api_query_dates.sort()
        else:
            # no query dates for future quotas
            api_query_dates = [None]

        return api_query_dates[0]

    @staticmethod
    def get_associated_measures(quota):
        """
        returns associated measures for the quota

        Args:
            quota: The quota to be queried

        Returns:
            TrackedModelQuerySet(Measures): A set of measures associated with the
            provided quota

        """
        measures = (
            Measure.objects.latest_approved()
            .filter(
                order_number=quota.order_number,
                valid_between__startswith__lte=quota.valid_between.upper,
            )
            .filter(
                Q(
                    valid_between__endswith__gte=quota.valid_between.upper,
                )
                | Q(
                    valid_between__endswith=None,
                ),
            )
        )

        return measures

    def get_goods_nomenclature_item_ids(self, quota):
        """
        collects associated item_ids for a quota

        Args:
            quota: The quota to be queried

        Returns:
            list(str): list of strings each containing the associated item_id for a
            measure

        """
        item_ids = []
        for measure in self.get_associated_measures(quota):
            item_ids.append(measure.goods_nomenclature.item_id)

        return item_ids

    def get_goods_nomenclature_headings(self, item_ids: List[str]):
        """
        returns a string representing the headings and descriptions for measures
        associated with a quota. Headings are at the 4 digit level, e.g. 1234000000

        Args:
            item_ids: list(str) : a list of strings representing item_ids

        Returns:
            str: unique headings and associated descriptions for each heading seperated
            by the "|" character (bar)
        """
        heading_item_ids = []
        headings = []

        for item_id in item_ids:
            heading_item_id = item_id[:4]
            if heading_item_id not in heading_item_ids:
                heading_and_desc = (
                    heading_item_id
                    + "-"
                    + self.get_goods_nomenclature_description(
                        heading_item_id + "000000",
                    )
                )
                headings.append(heading_and_desc)
                heading_item_ids.append(heading_item_id)

        return "|".join(headings)

    @staticmethod
    def get_goods_nomenclature_description(item_id):
        """
        returns the description associated with an item_id

        Args:
            item_id: the item_id to be queried

        Returns:
            str: the current description for the item_id
        """
        description = (
            GoodsNomenclatureDescription.objects.latest_approved()
            .filter(described_goods_nomenclature__item_id=item_id)
            .order_by("-validity_start")
            .first()
        )

        return description.description
