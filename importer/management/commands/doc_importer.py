import logging
from abc import ABCMeta, abstractmethod
from datetime import datetime
from typing import Iterator
from typing import List
from typing import Optional
from typing import TypeVar

from django.db import transaction

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


class RowsImporter(metaclass=ABCMeta):
    def __init__(
        self,
        workbasket: WorkBasket,
        serializer: EnvelopeSerializer,
        forward_time: datetime = BREXIT,
        first_run: bool = True,
    ) -> None:
        self.workbasket = workbasket
        self.serializer = serializer
        self.first_run = first_run

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

    def flush(self) -> Iterator[List[TrackedModel]]:
        return iter([])

    @abstractmethod
    def handle_row(
        self,
        new_row: Optional[NewRow],
        old_row: Optional[OldRow],
    ) -> Iterator[List[TrackedModel]]:
        ...

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

        logger.debug("Comparing old %s/%s [%s] and new %s/%s [%s]",
            old_row.item_id,
            old_row.goods_nomenclature.suffix if old_row.goods_nomenclature else None,
            old_row.goods_nomenclature.sid if old_row.goods_nomenclature else None,
            new_row.item_id,
            new_row.goods_nomenclature.suffix if new_row.goods_nomenclature else None,
            new_row.goods_nomenclature.sid if new_row.goods_nomenclature else None,
        )
        if old_row.item_id < new_row.item_id:
            return -1
        elif old_row.item_id > new_row.item_id:
            return 1
        return 0

    @transaction.atomic
    def import_sheets(
        self,
        new_rows: Iterator[NewRow],
        old_rows: Iterator[OldRow],
    ) -> None:
        setup_models = []
        for model in self.setup():
            model.save()
            setup_models.append(model)
        self.serializer.render_transaction(setup_models)

        new_row_generator = iter(new_rows)
        old_row_generator = iter(old_rows)
        new_row = next(new_row_generator, None)
        old_row = next(old_row_generator, None)
        old_row_count = 0
        while new_row or old_row:
            try:
                compare = self.compare_rows(new_row, old_row)
                if compare < 0:
                    # Old row comes before new row
                    # Hence it is a row we are not replacing
                    handle_args = (None, old_row)
                elif compare > 0:
                    # Old row comes after new row
                    # Hence new row is completely new
                    handle_args = (new_row, None)
                else:  # compare == 0
                    # Rows compared equal
                    # Hence new row is replacing the old row
                    handle_args = (new_row, old_row)

                for transaction in self.handle_row(*handle_args):
                    self._save_and_render_transaction(transaction)

            except Exception as ex:
                logger.error(
                    f"Explosion whilst handling {new_row.__dict__ if new_row else None} "
                    f"or {old_row.__dict__ if old_row else None}"
                )
                raise ex

            if compare <= 0:
                if old_row_count % 500 == 0:
                    logger.info("Progress: at row %d", old_row_count)
                old_row = next(old_row_generator, None)
                old_row_count += 1
            if compare >= 0:
                new_row = next(new_row_generator, None)

        # Final chance to flush any remaining rows
        for transaction in self.flush():
            self._save_and_render_transaction(transaction)

    def _save_and_render_transaction(self, transaction: List[TrackedModel]) -> None:
        for model in transaction:
            #model.clean_fields()
            #model.save()
            logger.debug("%s: %s", type(model), model.__dict__)
        if any(transaction):
            self.serializer.render_transaction(transaction)
