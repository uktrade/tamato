import logging
from functools import cached_property
from functools import lru_cache
from itertools import islice
from typing import Iterable
from typing import Iterator
from typing import List
from typing import Optional

import django
import xlrd
from django.core.management import BaseCommand
from django.db import transaction
from psycopg2._range import DateTimeTZRange
from xlrd.sheet import Cell

from certificates.models import Certificate
from certificates.models import CertificateDescription
from certificates.models import CertificateType
from commodities.models import FootnoteAssociationGoodsNomenclature
from commodities.models import GoodsNomenclature
from common.models import TrackedModel
from common.validators import UpdateType
from footnotes.models import Footnote
from footnotes.models import FootnoteDescription
from footnotes.models import FootnoteType
from footnotes.validators import ApplicationCode
from geo_areas.models import GeographicalArea
from importer.management.commands.doc_importer import RowsImporter
from importer.management.commands.import_sheet import SheetImporter
from importer.management.commands.patterns import BREXIT
from importer.management.commands.patterns import MeasureEndingPattern
from importer.management.commands.utils import clean_item_id
from importer.management.commands.utils import col
from importer.management.commands.utils import EnvelopeSerializer
from importer.management.commands.utils import get_author
from importer.management.commands.utils import id_argument
from importer.management.commands.utils import maybe_max
from importer.management.commands.utils import maybe_min
from importer.management.commands.utils import MeasureContext
from importer.management.commands.utils import MeasureTreeCollector
from importer.management.commands.utils import output_argument
from importer.management.commands.utils import spreadsheet_argument
from importer.management.commands.utils import strint
from measures.models import Measure
from measures.models import MeasureAction
from measures.models import MeasureCondition
from measures.models import MeasureConditionCode
from measures.models import MeasureType
from regulations.models import Regulation
from workbaskets.models import WorkBasket
from workbaskets.validators import WorkflowStatus

brexit_to_infinity = DateTimeTZRange(BREXIT, None)


logger = logging.getLogger(__name__)


class NewRow:
    def __init__(self, row: List[Cell]) -> None:
        self.taric_code = clean_item_id(row[col("B")])
        self.area_id = strint(row[col("C")])
        self.measure_type_id = strint(row[col("D")])
        self.positive_doc_type = strint(row[col("E")])
        self.positive_doc_id = strint(row[col("F")])
        self.negative_doc_type = strint(row[col("G")])
        self.negative_doc_id = strint(row[col("H")])
        self.regulation_role = int(row[col("I")].value)
        self.regulation_id = str(row[col("J")].value)
        self.footnote_id = str(row[col("K")].value)

    @cached_property
    def goods_nomenclature(self) -> GoodsNomenclature:
        try:
            return GoodsNomenclature.objects.as_at(BREXIT).get(
                item_id=self.taric_code,
                suffix="80",
            )
        except GoodsNomenclature.DoesNotExist:
            return None

    @cached_property
    def measure_context(self) -> MeasureContext:
        return MeasureContext(
            self.measure_type_id,
            self.area_id,
            None,
            None,
            None,
            None,
            BREXIT,
            None,
        )


class FootnoteAssociationRow:
    def __init__(self, row: List[Cell]) -> None:
        self.taric_code = clean_item_id(row[col("A")])
        self.footnote_type = str(row[col("B")].value)
        self.footnote_id = strint(row[col("C")])

    @cached_property
    def goods_nomenclature(self) -> GoodsNomenclature:
        try:
            return GoodsNomenclature.objects.as_at(BREXIT).get(
                item_id=self.taric_code,
                suffix="80",
            )
        except GoodsNomenclature.DoesNotExist:
            return None


class ExportControlMeasureImporter(RowsImporter):
    def setup(self) -> Iterator[TrackedModel]:
        self.new_rows = MeasureTreeCollector[NewRow](BREXIT)
        self.measure_ender = MeasureEndingPattern(
            workbasket=self.workbasket,
        )

        return iter([])

    @lru_cache
    def get_certificate(self, id: str, ctype: str) -> Certificate:
        return Certificate.objects.get(sid=id, certificate_type__sid=ctype)

    @lru_cache
    def get_regulation(self, id: str, role: str) -> Regulation:
        return Regulation.objects.get(role_type=role, regulation_id=id)

    @lru_cache
    def get_footnote(self, f: str) -> Footnote:
        return Footnote.objects.get(
            footnote_id=f[3:], footnote_type__footnote_type_id=f[0:2]
        )

    @lru_cache
    def get_measure_type(self, m: str) -> MeasureType:
        return MeasureType.objects.get(sid=m)

    @lru_cache
    def get_origin(self, area_id: str) -> GeographicalArea:
        return GeographicalArea.objects.get(area_id=area_id)

    @cached_property
    def presentation_of_certificate(self) -> MeasureConditionCode:
        return MeasureConditionCode.objects.get(code="B")

    @cached_property
    def export_allowed_after_control(self) -> MeasureAction:
        return MeasureAction.objects.get(code="29")

    @cached_property
    def export_not_allowed_after_control(self) -> MeasureAction:
        return MeasureAction.objects.get(code="09")

    def get_export_condition(
        self, measure: Measure, positive_doc: Certificate, negative_doc: Certificate
    ) -> Iterable[TrackedModel]:
        return [
            MeasureCondition(
                sid=self.counters["measure_condition_id"](),
                dependent_measure=measure,
                component_sequence_number=1,
                condition_code=self.presentation_of_certificate,
                required_certificate=positive_doc,
                action=self.export_allowed_after_control,
                update_type=UpdateType.CREATE,
                workbasket=self.workbasket,
            ),
            MeasureCondition(
                sid=self.counters["measure_condition_id"](),
                dependent_measure=measure,
                component_sequence_number=2,
                condition_code=self.presentation_of_certificate,
                required_certificate=negative_doc,
                action=self.export_allowed_after_control,
                update_type=UpdateType.CREATE,
                workbasket=self.workbasket,
            ),
            MeasureCondition(
                sid=self.counters["measure_condition_id"](),
                dependent_measure=measure,
                component_sequence_number=3,
                condition_code=self.presentation_of_certificate,
                action=self.export_not_allowed_after_control,
                update_type=UpdateType.CREATE,
                workbasket=self.workbasket,
            ),
        ]

    def get_export_measure(
        self, row: NewRow, cc: GoodsNomenclature
    ) -> Iterable[TrackedModel]:
        measure = Measure(
            sid=self.counters["measure_id"](),
            measure_type=self.get_measure_type(row.measure_type_id),
            geographical_area=self.get_origin(row.area_id),
            goods_nomenclature=cc,
            valid_between=brexit_to_infinity,
            generating_regulation=self.get_regulation(
                row.regulation_id, row.regulation_role
            ),
            update_type=UpdateType.CREATE,
            workbasket=self.workbasket,
        )

        conditions = self.get_export_condition(
            measure,
            self.get_certificate(row.positive_doc_id, row.positive_doc_type),
            self.get_certificate(row.negative_doc_id, row.negative_doc_type),
        )
        return [measure, *conditions]

    def handle_row(
        self, new_row: Optional[NewRow], old_row: None
    ) -> Iterator[List[TrackedModel]]:
        if new_row is not None and new_row.goods_nomenclature is not None:
            new_waiting = not self.new_rows.add(new_row.goods_nomenclature, new_row)
        else:
            logger.warning(
                "Missing row for %s", new_row.taric_code if new_row else None
            )
            new_waiting = False

        if new_waiting:
            for t in self.flush():
                yield t
            self.new_rows.reset()
            for t in self.handle_row(new_row, None):
                yield t

    def flush(self) -> Iterator[List[TrackedModel]]:
        for cc, row in self.new_rows.buffer():
            yield list(self.get_export_measure(row, cc))


class Command(BaseCommand):
    help = "Import spreadsheets of quotas and measures for trade agreements."

    def add_arguments(self, p):
        spreadsheet_argument(p, "new")
        id_argument(p, "measure", 200000000)
        id_argument(p, "measure-condition", 200000000)
        id_argument(p, "certificate-description", 5000)
        id_argument(p, "envelope")
        id_argument(p, "transaction", 140)
        output_argument(p)

    @transaction.atomic
    def handle(self, *args, **options):
        author = get_author()
        workbasket, _ = WorkBasket.objects.get_or_create(
            title=f"Export control measures from ECJU",
            author=author,
            status=WorkflowStatus.PUBLISHED,
        )

        workbook = xlrd.open_workbook(options["new-spreadsheet"])
        regulations_sheet = workbook.sheet_by_name("Legislation")
        footnotes_sheet = workbook.sheet_by_name("Footnotes")
        codes_footnotes_sheet = workbook.sheet_by_name("Codes-Footnotes")
        measures_sheet = workbook.sheet_by_name("Measures")

        with open(options["output"], mode="w", encoding="UTF8") as output:
            with EnvelopeSerializer(
                output,
                options["counters"]["envelope_id"](),
                options["counters"]["transaction_id"],
            ) as env:
                # Regulations
                regulation_importer = SheetImporter(
                    Regulation,
                    workbasket,
                    None,
                    "information_text",
                    None,
                    "regulation_group",
                    "approved",
                    "published_at",
                    None,
                    "valid_between[0]",
                    "role_type",
                    "regulation_id",
                    "public_identifier",
                    "url",
                )

                rows = islice(
                    regulations_sheet.get_rows(), options["new_skip_rows"], None
                )
                for instance in regulation_importer.import_rows(rows):
                    instance.save()
                    env.render_transaction([instance])

                # Footnotes
                ex_type, created = FootnoteType.objects.get_or_create(
                    footnote_type_id="EX",
                    application_code=ApplicationCode.CN_MEASURES,
                    description="Export control measures",
                    valid_between=brexit_to_infinity,
                    workbasket=workbasket,
                    update_type=UpdateType.CREATE,
                )
                if created:
                    env.render_transaction([ex_type])

                footnotes_importer = SheetImporter(
                    Footnote,
                    workbasket,
                    "footnote_type",
                    "footnote_id",
                    None,
                    "valid_between[0]",
                    None,
                )
                descriptions_importer = SheetImporter(
                    FootnoteDescription,
                    workbasket,
                    "described_footnote[1]",
                    "described_footnote[0]",
                    "description",
                    "valid_between[0]",
                    "description_period_sid",
                )

                footnotes = list(
                    footnotes_importer.import_rows(
                        islice(
                            footnotes_sheet.get_rows(), options["new_skip_rows"], None
                        )
                    )
                )
                footnote_lookup = {
                    (
                        footnote.footnote_type.footnote_type_id,
                        footnote.footnote_id,
                    ): footnote
                    for footnote in footnotes
                }
                for footnote in footnotes:
                    footnote.save()

                descriptions = list(
                    descriptions_importer.import_rows(
                        islice(
                            footnotes_sheet.get_rows(), options["new_skip_rows"], None
                        )
                    )
                )
                for footnote, desc in zip(footnotes, descriptions):
                    desc.save()
                    env.render_transaction([footnote, desc])

                # Negative docs
                cert = Certificate.objects.create(
                    sid="000",
                    certificate_type=CertificateType.objects.get(sid="X"),
                    valid_between=brexit_to_infinity,
                    workbasket=workbasket,
                    update_type=UpdateType.CREATE,
                )
                desc = CertificateDescription.objects.create(
                    sid=options["counters"]["certificate_description_id"](),
                    description="No licence required",
                    described_certificate=cert,
                    valid_between=brexit_to_infinity,
                    workbasket=workbasket,
                    update_type=UpdateType.CREATE,
                )
                env.render_transaction([cert, desc])

                # Footnotes on nomenclature
                for row in (
                    FootnoteAssociationRow(r)
                    for r in islice(
                        codes_footnotes_sheet.get_rows(), options["new_skip_rows"], None
                    )
                ):
                    if row.goods_nomenclature is None:
                        logger.warning("can't find gn %s", row.taric_code)
                        continue

                    footnote = footnote_lookup[(row.footnote_type, row.footnote_id)]
                    start_date = maybe_max(
                        BREXIT,
                        row.goods_nomenclature.valid_between.lower,
                        footnote.valid_between.lower,
                    )
                    end_date = maybe_min(
                        None,
                        row.goods_nomenclature.valid_between.upper,
                        footnote.valid_between.upper,
                    )

                    if end_date and end_date < start_date:
                        logger.warning(
                            "Skipping association as %s < %s", end_date, start_date
                        )
                        continue

                    instance = FootnoteAssociationGoodsNomenclature(
                        goods_nomenclature=row.goods_nomenclature,
                        associated_footnote=footnote,
                        valid_between=DateTimeTZRange(start_date, end_date),
                        workbasket=workbasket,
                        update_type=UpdateType.CREATE,
                    )
                    logger.debug("Create instance %s", instance.__dict__)
                    try:
                        instance.save()
                    except django.core.exceptions.ValidationError:
                        logger.error(
                            "Error on assoc GN %s/%s [%s] to footnote %s%s",
                            row.goods_nomenclature.item_id,
                            row.goods_nomenclature.suffix,
                            row.goods_nomenclature.sid,
                            footnote.footnote_type.footnote_type_id,
                            footnote.footnote_id,
                        )
                        raise

                    env.render_transaction([instance])

                # Measures
                measure_importer = ExportControlMeasureImporter(
                    workbasket=workbasket,
                    serializer=env,
                    counters=options["counters"],
                )
                area_ids = set(
                    strint(c)
                    for c in measures_sheet.col(
                        col("C"), start_rowx=options["new_skip_rows"]
                    )
                )
                for area in area_ids:
                    logger.info("Processing controls for area %s", area)
                    rows = islice(
                        measures_sheet.get_rows(), options["new_skip_rows"], None
                    )
                    measure_importer.import_sheets(
                        (r for r in (NewRow(r) for r in rows) if r.area_id == area),
                        iter([None]),
                    )

                transaction.set_rollback(True)
