import logging
from datetime import datetime
from typing import Generic
from typing import Iterator
from typing import List
from typing import Optional
from typing import TypeVar

import django.db

from common.models import TrackedModel
from importer.duty_sentence_parser import DutySentenceParser
from importer.management.commands.patterns import BREXIT
from importer.management.commands.utils import EnvelopeSerializer
from measures.models import DutyExpression
from measures.models import Measurement
from measures.models import MonetaryUnit
from workbaskets.models import WorkBasket

logger = logging.getLogger(__name__)

OldRow = TypeVar("OldRow")
NewRow = TypeVar("NewRow")


class RowsImporter(Generic[OldRow, NewRow]):
    def __init__(
        self,
        workbasket: WorkBasket,
        serializer: EnvelopeSerializer,
        forward_time: datetime = BREXIT,
    ) -> None:
        self.workbasket = workbasket
        self.serializer = serializer

        duty_expressions = (
            DutyExpression.objects.as_at(forward_time).order_by("sid")
            # 37 is literal nothing, which will match all strings
            .exclude(sid__exact=37)
        )
        monetary_units = MonetaryUnit.objects.as_at(forward_time)
        permitted_measurements = (
            Measurement.objects.as_at(forward_time)
            .exclude(measurement_unit__abbreviation__exact="")
            .exclude(
                measurement_unit_qualifier__abbreviation__exact="",
            )
        )

        self.duty_sentence_parser = DutySentenceParser(
            duty_expressions, monetary_units, permitted_measurements
        )

        self.counters = {}
        self.last_new_item_id = None
        self.last_old_item_id = None

    def setup(self) -> Iterator[TrackedModel]:
        return iter([])

    def compare_rows(self, new_row: Optional[NewRow], old_row: Optional[OldRow]) -> int:
        if new_row is None:
            return -1
        if old_row is None:
            return 1

        if self.last_old_item_id is not None:
            assert (
                self.last_old_item_id <= old_row.item_id
            ), f"Old rows out of order around {old_row.item_id}"
        self.last_old_item_id = old_row.item_id

        if self.last_new_item_id is not None:
            assert (
                self.last_new_item_id <= new_row.item_id
            ), f"New rows out of order around {new_row.item_id}"
        self.last_new_item_id = new_row.item_id

        logger.debug("Comparing old %s and new %s", old_row.item_id, new_row.item_id)
        if old_row.item_id < new_row.item_id:
            return -1
        elif old_row.item_id > new_row.item_id:
            return 1
        else:
            return 0

    def handle_row(
        self,
        new_row: Optional[NewRow],
        old_row: Optional[OldRow],
    ) -> Iterator[List[TrackedModel]]:
        raise NotImplementedError("Override this")

    def import_sheets(
        self,
        new_rows: Iterator[NewRow],
        old_rows: Iterator[OldRow],
        skip_new_rows: int = 0,
        skip_old_rows: int = 0,
    ) -> None:
        with django.db.transaction.atomic():
            setup_models = []
            for model in self.setup():
                model.full_clean()
                model.save()
                setup_models.append(model)
            self.serializer.render_transaction(setup_models)

            new_row_generator = enumerate(new_rows)
            old_row_generator = enumerate(old_rows)
            new_row_number, new_row = next(new_row_generator)
            old_row_number, old_row = next(old_row_generator)

            while new_row or old_row:
                new_consume = False
                old_consume = False
                if old_row_number < skip_old_rows:
                    old_consume = True
                if new_row_number < skip_new_rows:
                    new_consume = True

                if not old_consume and not new_consume:
                    try:
                        compare = self.compare_rows(new_row, old_row)
                        if compare < 0:
                            # Old row comes before new row
                            # Hence it is a row we are not replacing
                            old_consume = old_row is not None
                            handle_args = (None, old_row)
                        elif compare > 0:
                            # Old row comes after new row
                            # Hence new row is completely new
                            new_consume = new_row is not None
                            handle_args = (new_row, None)
                        else:  # compare == 0
                            # Rows compared equal
                            # Hence new row is replacing the old row
                            old_consume = old_row is not None
                            new_consume = new_row is not None
                            handle_args = (new_row, old_row)

                        tracked_models = []
                        for transaction in self.handle_row(*handle_args):
                            # model.clean_fields()
                            # model.save()
                            for model in transaction:
                                logger.debug("%s: %s", type(model), model.__dict__)
                            if any(transaction):
                                self.serializer.render_transaction(transaction)

                        if new_row_number % 500 == 0:
                            logger.info("Progress: at row %d", new_row_number)
                    except Exception as ex:
                        logger.error(
                            f"Explosion whilst handling {new_row.__dict__ if new_row else None} or {old_row.__dict__ if old_row else None}"
                        )
                        raise ex

                try:
                    if old_consume:
                        old_row_number, old_row = next(old_row_generator)
                except StopIteration:
                    old_row = None

                try:
                    if new_consume:
                        new_row_number, new_row = next(new_row_generator)
                except StopIteration:
                    new_row = None

            for name, counter in self.counters.items():
                logger.info("Next %s: %s", name, counter())
            logger.info("Import complete")
