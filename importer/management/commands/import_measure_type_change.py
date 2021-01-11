from datetime import datetime
from typing import Dict
from typing import Iterator
from typing import List
from typing import Optional

from dateutil.relativedelta import relativedelta
from psycopg2._range import DateTimeTZRange

from common.models import TrackedModel
from common.validators import UpdateType
from importer.management.commands.doc_importer import RowsImporter
from importer.management.commands.import_command import ImportCommand
from importer.management.commands.patterns import BREXIT
from importer.management.commands.patterns import LONDON
from importer.management.commands.patterns import MeasureCreatingPattern
from importer.management.commands.patterns import OldMeasureRow
from importer.management.commands.utils import Counter
from importer.management.commands.utils import EnvelopeSerializer
from importer.management.commands.utils import id_argument
from importer.management.commands.utils import maybe_min
from importer.management.commands.utils import spreadsheet_argument
from measures.models import Measure
from measures.models import MeasureType
from regulations.models import Regulation
from workbaskets.models import WorkBasket

CUSTOMS_UNION_EQUIVALENT_TYPES = {
    "142": MeasureType.objects.get(sid="106"),
    "143": MeasureType.objects.get(sid="147"),
}


class MeasureTypeChangingImporter(RowsImporter):
    def __init__(
        self,
        workbasket: WorkBasket,
        serializer: EnvelopeSerializer,
        counters: Dict[str, Counter],
        first_run: bool,
    ) -> None:
        self.changeover_date = LONDON.localize(datetime(2021, 1, 20))
        super().__init__(
            workbasket,
            serializer,
            forward_time=self.changeover_date,
            counters=counters,
            first_run=first_run,
        )

    def setup(self) -> Iterator[TrackedModel]:
        self.preferential_si = Regulation.objects.get(regulation_id="C2100006")

        self.measure_creator = MeasureCreatingPattern(
            generating_regulation=self.preferential_si,
            workbasket=self.workbasket,
            duty_sentence_parser=self.duty_sentence_parser,
            measure_sid_counter=self.counters["measure_id"],
            measure_condition_sid_counter=self.counters["measure_condition_id"],
        )

        return super().setup()

    def handle_row(
        self, new_row: None, row: Optional[OldMeasureRow]
    ) -> Iterator[List[TrackedModel]]:
        assert new_row is None
        if row.measure_start_date >= self.changeover_date:
            return

        ends_before_changeover = (
            row.measure_end_date and row.measure_end_date <= self.changeover_date
        )
        ends_after_changeover = (
            row.measure_end_date and row.measure_end_date > self.changeover_date
        )
        if ends_before_changeover:
            new_start_date = row.measure_start_date
            new_end_date = row.measure_end_date
            terminating_regulation = row.justification_regulation
            update_type = UpdateType.DELETE
        else:
            new_start_date = self.changeover_date
            new_end_date = row.measure_end_date  # maybe None
            terminating_regulation = row.justification_regulation  # maybe None
            update_type = UpdateType.UPDATE

        # Update old measure
        yield [
            Measure(
                sid=row.measure_sid,
                measure_type=row.measure_type_object,
                geographical_area=row.geographical_area,
                goods_nomenclature=row.goods_nomenclature,
                valid_between=DateTimeTZRange(
                    lower=new_start_date,
                    upper=new_end_date,
                ),
                generating_regulation=row.measure_generating_regulation,
                terminating_regulation=terminating_regulation,
                order_number=row.quota,
                additional_code=row.additional_code,
                update_type=update_type,
                workbasket=self.workbasket,
            )
        ]

        # Create customs union measure
        cu_end_date = maybe_min(
            self.changeover_date - relativedelta(days=1), row.measure_end_date
        )
        yield list(
            self.measure_creator.create(
                duty_sentence=row.duty_expression,
                geography=row.geographical_area,
                goods_nomenclature=row.goods_nomenclature,
                new_measure_type=CUSTOMS_UNION_EQUIVALENT_TYPES[row.measure_type],
                order_number=row.quota,
                validity_start=row.measure_start_date,
                validity_end=cu_end_date,
            )
        )


class Command(ImportCommand):
    help = "Change the measure type on measures preferences before a certain date"
    title = "Push back tariff preferences and introduce Customs Union preferences for Turkey"

    def add_arguments(self, parser) -> None:
        spreadsheet_argument(parser, "old")
        id_argument(parser, "measure")
        id_argument(parser, "measure-condition")
        super().add_arguments(parser)

    def run(self, workbasket: WorkBasket, env: EnvelopeSerializer) -> None:
        measure_rows = (
            OldMeasureRow(r) for r in self.get_sheet("old", "Sheet", skip=1)
        )

        MeasureTypeChangingImporter(
            workbasket=workbasket,
            serializer=env,
            counters=self.options["counters"],
            first_run=True,
        ).import_sheets(
            iter([None]),
            measure_rows,
        )
