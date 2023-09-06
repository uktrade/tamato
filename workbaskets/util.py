import re
from datetime import date

from django.db import transaction
from parsec import ParseError

from commodities.validators import ITEM_ID_REGEX
from common.util import TaricDateRange
from importer.nursery import get_nursery


@transaction.atomic
def clear_workbasket(workbasket):
    """
    Deletes all objects connected to the workbasket while preserving the
    workbasket itself.

    Due to the DB relations this has to be done in a specific order.

    - First the Tracked Models must be deleted in reverse order.
        - As these are deleted their VersionGroups must be deleted
          or reset to have the previous version as current.
        - Also if any of these exist within the cache they must
          be removed from the cache.
    - Second Transactions are deleted.
    """
    nursery = get_nursery()

    for obj in workbasket.tracked_models.order_by("-pk"):
        version_group = obj.version_group
        obj.delete()
        nursery.remove_object_from_cache(obj)
        if version_group.versions.count() == 0:
            version_group.delete()
        else:
            version_group.current_version = version_group.versions.order_by(
                "-pk",
            ).first()
            version_group.save()

    workbasket.transactions.all().delete()


@transaction.atomic
def delete_workbasket(workbasket):
    """Deletes all objects connected to the workbasket and the workbasket
    itself."""
    clear_workbasket(workbasket)
    workbasket.delete()


# permits both date formats
# YYYY-MM-DD
# DD-MM-YYYY
# and either - or / separator
DATE_REGEX = (
    r"([0-9]{2}(\/|-)[0-9]{2}(\/|-)[0-9]{4})|([0-9]{4}(\/|-)[0-9]{2}(\/|-)[0-9]{2})"
)


class TableRow:
    def __init__(self, commodity=None, valid_between=None, duty_sentence=None):
        self.commodity = commodity
        self.valid_between = valid_between
        self.duty_sentence = duty_sentence

    @property
    def all_none(self):
        return not any([self.commodity, self.valid_between, self.duty_sentence])


def find_comm_code(cell, row_data):
    from commodities.models.orm import GoodsNomenclature

    matches = re.compile(ITEM_ID_REGEX).match(cell)
    if matches:
        commodity = (
            GoodsNomenclature.objects.latest_approved().filter(item_id=cell).first()
        )
        row_data.commodity = commodity
        return True
    return False


def find_date(cell):
    matches = re.compile(DATE_REGEX).match(cell)
    if matches:
        return cell


def find_duty_sentence(cell, row_data):
    from measures.parsers import DutySentenceParser

    # because we may not know the measure validity period, take today's date instead
    # we only need to look for something that looks like a duty sentence, not necessarily a valid one
    duty_sentence_parser = DutySentenceParser.create(
        date.today(),
    )
    duty_sentence = cell.replace(" ", "")
    try:
        duty_sentence_parser.parse(duty_sentence)
        row_data.duty_sentence = cell
        return True
    except ParseError:
        return False


def get_delimiter(date_string):
    if "/" in date_string:
        return "/"
    elif "-" in date_string:
        return "-"
    return None


def parse_dates(dates):
    parsed_dates = []
    for date_string in dates:
        delimiter = get_delimiter(date_string)
        components = [int(component) for component in date_string.split(delimiter)]

        # year first
        if components[0] > 1000:
            parsed_dates.append(
                date(components[0], components[1], components[2]),
            )
        # year last
        elif components[-1] > 1000:
            parsed_dates.append(
                date(components[2], components[1], components[0]),
            )
    return parsed_dates


def assign_validity(dates, row_data):
    parsed_dates = parse_dates(dates)

    # assume start date for an open-ended measure
    if len(parsed_dates) == 1:
        row_data.valid_between = TaricDateRange(
            parsed_dates[0],
            None,
        )
    elif len(parsed_dates) == 2:
        if parsed_dates[0] > parsed_dates[1]:
            row_data.valid_between = TaricDateRange(
                parsed_dates[1],
                parsed_dates[0],
            )
        elif parsed_dates[1] > parsed_dates[0]:
            row_data.valid_between = TaricDateRange(
                parsed_dates[0],
                parsed_dates[1],
            )


def serialize_uploaded_data(data):
    serialized = []
    rows = data.strip().split("\n")
    table = [row.strip().split("\t") for row in rows]

    for row in table:
        row_data = TableRow()
        dates = []
        for cell in row:
            if not cell:
                continue

            commodity = find_comm_code(cell, row_data)
            if commodity:
                continue

            found_date = find_date(cell)
            if found_date:
                dates.append(found_date)
                continue

            duty_sentence = find_duty_sentence(cell, row_data)
            if duty_sentence:
                continue

        assign_validity(dates, row_data)

        if not row_data.all_none:
            serialized.append(row_data)

    return serialized
