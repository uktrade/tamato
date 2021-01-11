import logging
from functools import cached_property
from itertools import islice
from typing import Dict
from typing import Iterator
from typing import List
from typing import Optional
from typing import Tuple

import xlrd
from django.core.management import BaseCommand
from django.db import transaction
from psycopg2._range import DateTimeTZRange
from xlrd.sheet import Cell

from commodities.models import GoodsNomenclature
from common.models import TrackedModel
from common.validators import UpdateType
from geo_areas.models import GeographicalArea
from geo_areas.models import GeographicalMembership
from importer.management.commands.doc_importer import RowsImporter
from importer.management.commands.patterns import BREXIT
from importer.management.commands.patterns import DualRowRunner
from importer.management.commands.patterns import MeasureCreatingPattern
from importer.management.commands.patterns import MeasureEndingPattern
from importer.management.commands.patterns import OldMeasureRow
from importer.management.commands.patterns import add_single_row
from importer.management.commands.quota_importer import QuotaImporter
from importer.management.commands.quota_importer import QuotaRow
from importer.management.commands.quota_importer import QuotaSource
from importer.management.commands.utils import EnvelopeSerializer
from importer.management.commands.utils import MeasureContext
from importer.management.commands.utils import MeasureTreeCollector
from importer.management.commands.utils import clean_duty_sentence
from importer.management.commands.utils import clean_item_id
from importer.management.commands.utils import col
from importer.management.commands.utils import get_author
from importer.management.commands.utils import id_argument
from importer.management.commands.utils import output_argument
from importer.management.commands.utils import spreadsheet_argument
from importer.management.commands.utils import write_summary
from measures.models import MeasureType
from quotas.models import QuotaDefinition
from quotas.models import QuotaOrderNumber
from quotas.validators import AdministrationMechanism
from quotas.validators import QuotaCategory
from regulations.models import Group
from regulations.models import Regulation
from workbaskets.models import WorkBasket
from workbaskets.validators import WorkflowStatus

logger = logging.getLogger(__name__)


class WTOMeasureRow:
    def __init__(self, row: List[Cell]) -> None:
        self.item_id = clean_item_id(row[col("A")])
        self.quota_number = str(row[col("C")].value).strip()
        self.authorised_use = bool(row[col("D")].value)
        self.duty_exp = clean_duty_sentence(row[col("G")])
        self.preferential = bool(row[col("H")].value)

    @cached_property
    def goods_nomenclature(self) -> GoodsNomenclature:
        try:
            return GoodsNomenclature.objects.as_at(BREXIT).get(
                item_id=self.item_id, suffix="80"
            )
        except GoodsNomenclature.DoesNotExist as ex:
            logger.warning("Failed to find goods nomenclature %s", self.item_id)
            return None

    @cached_property
    def measure_type(self) -> str:
        if not self.preferential and not self.authorised_use:
            return "122"
        elif not self.preferential and self.authorised_use:
            return "123"
        elif self.preferential and not self.authorised_use:
            return "143"
        else:
            return "146"


class WTOMeasureImporter(RowsImporter):
    def __init__(self, *args, quotas=Dict[str, QuotaRow], **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.quotas = quotas

    @cached_property
    def non_pref_quota_type(self) -> MeasureType:
        return MeasureType.objects.get(sid="122")

    @cached_property
    def non_pref_authorised_use_quota_type(self) -> MeasureType:
        return MeasureType.objects.get(sid="123")

    @cached_property
    def pref_quota_type(self) -> MeasureType:
        return MeasureType.objects.get(sid="143")

    @cached_property
    def pref_authorised_use_quota_type(self) -> MeasureType:
        return MeasureType.objects.get(sid="146")

    def setup(self) -> Iterator[TrackedModel]:
        self.measure_types = {
            "122": self.non_pref_quota_type,
            "123": self.non_pref_authorised_use_quota_type,
            "143": self.pref_quota_type,
            "146": self.pref_authorised_use_quota_type,
        }
        ##self.old_rows = MeasureTreeCollector[OldMeasureRow](BREXIT)
        ##self.new_rows = MeasureTreeCollector[WTOMeasureRow](BREXIT)
        ##self.row_runner = DualRowRunner(
        ##    self.old_rows,
        ##    self.new_rows,  # TODO
        ##    add_old_row=add_single_row,
        ##    add_new_row=add_single_row,
        ##)

        self.brexit_to_infinity = DateTimeTZRange(BREXIT, None)

        self.wto_si, created = Regulation.objects.get_or_create(
            regulation_id="C2100020",  # TODO
            defaults={
                "regulation_group": Group.objects.get(group_id="KON"),  # TODO
                "information_text": "The Customs (Tariff Quotas) (EU Exit) Regulations 2020",
                "published_at": BREXIT,
                "approved": False,
                "valid_between": self.brexit_to_infinity,
                "workbasket": self.workbasket,
                "update_type": UpdateType.CREATE,
            },
        )
        if created:
            yield self.wto_si

        self.measure_ender = MeasureEndingPattern(
            workbasket=self.workbasket,
            measure_types=self.measure_types,
        )

        self.measure_creator = MeasureCreatingPattern(
            generating_regulation=self.wto_si,
            workbasket=self.workbasket,
            duty_sentence_parser=self.duty_sentence_parser,
            measure_sid_counter=self.counters["measure_id"],
            measure_condition_sid_counter=self.counters["measure_condition_id"],
        )

        if not created:
            return iter([])

    def handle_row(
        self, new_row: Optional[WTOMeasureRow], old_row: Optional[OldMeasureRow]
    ) -> Iterator[List[TrackedModel]]:
        # Send the old row to be end dated or removed
        if old_row is not None:
            logger.debug("End-dating measure: %s", old_row.measure_sid)
            yield list(self.measure_ender.end_date_measure(old_row, self.wto_si))

        # Create measures either for the single measure type or a mix
        if new_row is not None and new_row.goods_nomenclature is not None:
            if new_row.quota_number not in self.quotas:
                logger.warning(
                    "Skipping row with missing quota %s", new_row.quota_number
                )
                return

            quota_row = self.quotas[new_row.quota_number]
            quota = QuotaOrderNumber.objects.get(order_number=new_row.quota_number)
            assert quota_row.end_use == new_row.authorised_use
            for date_range in self.get_measure_dates(quota_row):
                for origin in quota_row.origins:
                    yield list(
                        self.measure_creator.create(
                            duty_sentence=new_row.duty_exp,
                            geography=origin,
                            goods_nomenclature=new_row.goods_nomenclature,
                            new_measure_type=self.measure_types[new_row.measure_type],
                            exclusions=quota_row.excluded_origins,
                            order_number=quota,
                            authorised_use=new_row.authorised_use,
                            validity_start=date_range.lower,
                            validity_end=date_range.upper,
                        )
                    )

    def get_measure_dates(self, row: QuotaRow) -> Iterator[DateTimeTZRange]:
        if row.mechanism == AdministrationMechanism.LICENSED:
            yield self.brexit_to_infinity
        else:
            definitions = QuotaDefinition.objects.filter(
                order_number__order_number=row.order_number,
            ).all()
            for definition in definitions:
                yield definition.valid_between


def add_members_to_group(from_group: GeographicalArea, to_group: GeographicalArea, workbasket: WorkBasket) -> Iterator[TrackedModel]:
    for membership in GeographicalMembership.objects.as_at(BREXIT).filter(
        geo_group=from_group
    ):
        if (
            not GeographicalMembership.objects.as_at(BREXIT)
            .filter(geo_group=to_group, member=membership.member)
            .exists()
        ):
            logger.debug(
                "Adding %s to %s",
                membership.member.area_id,
                to_group.area_id,
            )
            m = GeographicalMembership(
                geo_group=to_group,
                member=membership.member,
                valid_between=DateTimeTZRange(BREXIT, None),
                update_type=UpdateType.CREATE,
                workbasket=workbasket,
            )
            m.save()
            yield m


class Command(BaseCommand):
    help = "Import spreadsheets of quotas and measures for WTO agreements."

    def add_arguments(self, p):
        spreadsheet_argument(p, "new")
        spreadsheet_argument(p, "old")
        spreadsheet_argument(p, "quota")
        id_argument(p, "measure", 200000000)
        id_argument(p, "measure-condition", 200000000)
        id_argument(p, "quota-order-number")
        id_argument(p, "quota-order-number-origin")
        id_argument(p, "quota-definition")
        id_argument(p, "quota-suspension")
        id_argument(p, "envelope")
        id_argument(p, "transaction", 140)
        output_argument(p)

    @transaction.atomic()
    def handle(self, *args, **options):
        author = get_author()

        quota_workbook = xlrd.open_workbook(options["quota-spreadsheet"])
        quota_sheet = quota_workbook.sheet_by_name("ALL")
        new_workbook = xlrd.open_workbook(options["new-spreadsheet"])
        new_worksheet = new_workbook.sheet_by_name("MAIN")
        old_workbook = xlrd.open_workbook(options["old-spreadsheet"])
        old_worksheet = old_workbook.sheet_by_name("Sheet")

        workbasket, _ = WorkBasket.objects.get_or_create(
            title=f"WTO quota measures",
            author=author,
            status=WorkflowStatus.PUBLISHED,
        )

        with open(options["output"], mode="w", encoding="UTF8") as output:
            with EnvelopeSerializer(
                output,
                options["counters"]["envelope_id"](),
                options["counters"]["transaction_id"],
                max_envelope_size_in_mb=40,
            ) as env:
                #eu_group = GeographicalArea.objects.get(area_id="1013")
                #erga_omnes = GeographicalArea.objects.get(area_id="1011")
                #wto_countries = GeographicalArea.objects.get(area_id="2500")
                #for model in add_members_to_group(eu_group, erga_omnes, workbasket):
                #    env.render_transaction([model])
                #for model in add_members_to_group(eu_group, wto_countries, workbasket):
                #    env.render_transaction([model])

                quota_importer = QuotaImporter(
                    workbasket,
                    env,
                    category=QuotaCategory.WTO,
                    counters=options["counters"],
                    critical_interim=True,
                )

                quota_rows = (
                    QuotaRow(row)
                    for row in islice(
                        quota_sheet.get_rows(), options["quota_skip_rows"], None
                    )
                )

                quota_importer.import_sheets(
                    (
                        r
                        for r in quota_rows
                        if r.source == QuotaSource.WTO and "NO DEAL" not in r.origin_ids
                    ),
                    iter([None]),
                )

                measure_importer = WTOMeasureImporter(
                    workbasket,
                    env,
                    counters=options["counters"],
                    quotas=quota_importer.quotas,
                )

                old_rows = islice(
                    old_worksheet.get_rows(), options["old_skip_rows"], None
                )
                new_rows = islice(
                    new_worksheet.get_rows(), options["new_skip_rows"], None
                )
                measure_importer.import_sheets(
                    iter([None]),
                    (OldMeasureRow(r) for r in old_rows),
                )
                measure_importer.import_sheets(
                    (WTOMeasureRow(r) for r in new_rows),
                    iter([None]),
                )

        transaction.set_rollback(True)
        write_summary(
            options["output"],
            workbasket.title,
            options["counters"],
            options["counters__original"],
        )
