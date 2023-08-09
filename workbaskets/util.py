import re
from datetime import date

from django.core.exceptions import ValidationError
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


DATE_REGEX = (
    r"([0-9]{2}(\/|-)[0-9]{2}(\/|-)[0-9]{4})|([0-9]{4}(\/|-)[0-9]{2}(\/|-)[0-9]{2})"
)


class TableRow:
    def __init__(self, commodity=None, valid_between=None, duty=None):
        self.commodity = commodity
        self.valid_between = valid_between
        self.duty = duty


def serialize_uploaded_data(data):
    serialized = []
    rows = data.strip().split("\n")
    table = [row.strip().split("\t") for row in rows]
    from commodities.models.orm import GoodsNomenclature

    for row in table:
        row_data = TableRow()
        dates = []
        for cell in row:
            # look for comm code
            matches = re.compile(ITEM_ID_REGEX).match(cell)
            if matches:
                commodity = (
                    GoodsNomenclature.objects.latest_approved()
                    .filter(item_id=cell)
                    .first()
                )
                row_data.commodity = commodity
                continue
            # look for dates
            matches = re.compile(DATE_REGEX).match(cell)
            if matches:
                dates.append(cell)
                continue

            # look for duty sentence
            # if it didn't match comm code or date it's probably a duty
            row_data.duty = cell
            continue

        if len(dates) == 2:
            # should only have 2 dates - start and end
            if "/" in dates[0]:
                delimiter = "/"
            elif "-" in dates[0]:
                delimiter = "-"
            parsed_dates = []
            for date_string in dates:
                components = [
                    int(component) for component in date_string.split(delimiter)
                ]

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

        # if only one date this must be the start date
        elif len(dates) == 1:
            start_date = dates[0]

            if "/" in start_date:
                delimiter = "/"
            elif "-" in start_date:
                delimiter = "-"

            components = [int(component) for component in start_date.split(delimiter)]

            # year first
            if components[0] > 1000:
                row_data.valid_between = TaricDateRange(
                    date(components[0], components[1], components[2]),
                )
            # year last
            elif components[-1] > 1000:
                row_data.valid_between = TaricDateRange(
                    date(components[2], components[1], components[0]),
                )

        from measures.parsers import DutySentenceParser

        duty_sentence_parser = DutySentenceParser.create(
            row_data.valid_between.lower,
        )

        if row_data.duty:
            try:
                duty_sentence_parser.parse(row_data.duty)
            except ParseError as error:
                error_index = int(error.loc().split(":", 1)[1])
                raise ValidationError(
                    f'"{row_data.duty[error_index:]}" is an invalid duty expression',
                )

        serialized.append(row_data)
    return serialized
