import logging
from datetime import date
from typing import List

from django.db.models import Q

from commodities.models import GoodsNomenclatureDescription
from measures.models import Measure
from quotas.models import QuotaOrderNumberOrigin, QuotaSuspension, QuotaBlocking


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


def get_goods_nomenclature_headings(item_ids: List[str]):
    """
    Returns a string representing the headings and descriptions for measures
    associated with a quota. Headings are at the 4 digit level, e.g.
    1234000000.

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
                    + " - "
                    + get_goods_nomenclature_description(
                heading_item_id + "000000",
            )
            )
            headings.append(heading_and_desc)
            heading_item_ids.append(heading_item_id)

    return headings


def get_goods_nomenclature_description(item_id):
    """
    Returns the description associated with an item_id.

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


def get_goods_nomenclature_item_ids(quota):
    """
    Collects associated item_ids for a quota.

    Args:
        quota: The quota to be queried

    Returns:
        list(str): list of strings each containing the associated item_id for a
        measure
    """
    item_ids = []

    for measure in get_associated_measures(quota):
        item_ids.append(measure.goods_nomenclature.item_id)

    return item_ids


def get_associated_measures(quota):
    """
    Returns associated measures for the quota.

    Args:
        quota: The quota to be queried

    Returns:
        TrackedModelQuerySet(Measures): A set of measures associated with the
        provided quota
    """

    quota_order_number_ids = list(quota.order_number.get_versions().values_list('trackedmodel_ptr_id', flat=True))

    measures = (
        Measure.objects.latest_approved()
        .filter(
            order_number__trackedmodel_ptr_id__in=quota_order_number_ids,
            valid_between__startswith__lte=quota.valid_between.upper,
        )
        .filter(
            Q(
                valid_between__endswith__gte=quota.valid_between.lower,
            )
            | Q(
                valid_between__endswith=None,
            ),
        )
    )

    return measures


def get_measurement_unit(quota):
    """
    Returns the measurement unit associated with a Quota as a string.

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


def get_monetary_unit(quota):
    """
    Returns the monetary unit associated with a Quota as a string.

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


def get_geographical_areas_and_exclusions(quota):
    """
    Returns a tuple of geographical areas and exclusions associated with a
    Quota.

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


def get_suspension_periods_dates(quota):
    # get all it's for all quota updates
    quota_historic_ids = list(quota.get_versions().values_list('trackedmodel_ptr_id', flat=True))

    quota_suspension_periods = QuotaSuspension.objects.latest_approved().filter(quota_definition__trackedmodel_ptr_id__in=quota_historic_ids)
    result = []
    for suspension_period in quota_suspension_periods:
        result.append(
            [
                suspension_period.valid_between.lower.isoformat(),
                suspension_period.valid_between.upper.isoformat()
            ])
    return result


def get_blocking_periods_dates(quota):
    quota_blocking_periods = QuotaBlocking.objects.latest_approved().filter(quota_definition=quota)
    result = []
    for blocking_period in quota_blocking_periods:
        result.append([
            blocking_period.valid_between.lower.isoformat(),
            blocking_period.valid_between.upper.isoformat()
        ])
    return result


def get_api_query_date(quota):
    """
    Returns the most appropriate date for querying the HMRC API.
    Dates are checked against current date and collected, the oldest of
    the dates is used as the API query date. Typically, this wil be today's date
    or the end date of the quota if < today's date
    note: quotas that start in the future will not be populated on the HMRC API so
    None s returned to indicate this query can be safely skipped
    Args:
        quota: The quota to be queried
    Returns:
        str(of date) or none: a string of a date if available or none if quota is in the future
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
        api_query_dates = [None]

    if isinstance(api_query_dates[0], date):
        return str(api_query_dates[0])
    else:
        return api_query_dates[0]
