import logging
import sys
from collections import defaultdict
from datetime import timedelta
from typing import List

import django
import xlrd
from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from psycopg2._range import DateTimeTZRange
from xlrd.sheet import Cell

from commodities.models import GoodsNomenclature, GoodsNomenclatureIndent, GoodsNomenclatureDescription, \
    GoodsNomenclatureOrigin, GoodsNomenclatureSuccessor, FootnoteAssociationGoodsNomenclature
from common.renderers import counter_generator
from common.validators import UpdateType
from footnotes.models import Footnote
from geo_areas.models import GeographicalArea
from importer.management.commands.import_reliefs import EUR_GBP_CONVERSION_RATE
from importer.management.commands.patterns import BREXIT, MeasureCreatingPatternWithExpression, OldMeasureRow, \
    MeasureEndingPattern, parse_date
from importer.management.commands.utils import EnvelopeSerializer, parse_duty_parts, update_geo_area_description, blank
from measures.models import MeasureType
from regulations.models import Regulation
from workbaskets.models import WorkBasket
from workbaskets.validators import WorkflowStatus


logger = logging.getLogger(__name__)


BREXIT_TO_INFINITY = DateTimeTZRange(BREXIT, None)


class OperationType:
    GN = 0
    INDENT = 1
    DESCRIPTION = 2
    ORIGIN = 3
    SUCCESSOR = 4
    FOOTNOTE = 5


class CCOperationRow:
    def __init__(self, old_row: List[Cell]) -> None:
        self.operation_seq_id = int(old_row[0].value)
        self.type = int(old_row[1].value)
        if str(old_row[2].value) == 'C':
            self.update_type = UpdateType.CREATE
        elif str(old_row[2].value) == 'U':
            self.update_type = UpdateType.UPDATE
        elif str(old_row[2].value) == 'D':
            self.update_type = UpdateType.DELETE
        else:
            raise ValueError('Unknown operation update type')
        self.goods_nomenclature_sid = int(old_row[3].value)
        self.goods_nomenclature_item_id = blank(
            old_row[4].value, lambda _: str(old_row[4].value)
        )
        self.productline_suffix = blank(
            old_row[5].value, lambda _: str(old_row[5].value)
        )
        self.gn_validity_start_date = blank(
            old_row[6].value, lambda _: parse_date(old_row[6])
        )
        self.gn_validity_end_date = blank(
            old_row[7].value, lambda _: parse_date(old_row[7])
        )
        self.statistical_indicator = blank(
            old_row[8].value, lambda _: int(old_row[8].value)
        )
        self.goods_nomenclature_indent_sid = blank(
            old_row[9].value, lambda _: int(old_row[9].value)
        )
        self.indent_validity_start_date = blank(
            old_row[10].value, lambda _: parse_date(old_row[10])
        )
        self.number_indents = blank(
            old_row[11].value, lambda _: int(old_row[11].value)
        )
        self.description = blank(
            old_row[12].value, lambda _: str(old_row[12].value)
        )
        self.goods_nomenclature_description_period_sid = blank(
            old_row[13].value, lambda _: int(old_row[13].value)
        )
        self.desc_validity_start_date = blank(
            old_row[14].value, lambda _: parse_date(old_row[14])
        )
        self.derived_goods_nomenclature_sid = blank(
            old_row[15].value, lambda _: int(old_row[15].value)
        )
        self.measure_transfer_candidate = str(old_row[16].value) == 't'
        self.absorbed_goods_nomenclature_sid = blank(
            old_row[17].value, lambda _: int(old_row[17].value)
        )
        self.footnote_type = blank(
            old_row[18].value, lambda _: str(old_row[18].value)
        )
        self.footnote_id = blank(
            old_row[19].value, lambda _: str(old_row[19].value)
        )
        self.fn_validity_start_date = blank(
            old_row[20].value, lambda _: parse_date(old_row[20])
        )
        self.fn_validity_end_date = blank(
            old_row[21].value, lambda _: parse_date(old_row[21])
        )


class Command(BaseCommand):
    help = ""

    def add_arguments(self, parser):
        parser.add_argument(
            "--spreadsheet",
            help="The XLSX file containing measures to be parsed.",
            type=str,
            default=None,
        )
        parser.add_argument(
            "--measure-sid",
            help="The SID value to use for the first new measure",
            type=int,
            default=1,
        )
        parser.add_argument(
            "--measure-condition-sid",
            help="The SID value to use for the first new measure condition",
            type=int,
            default=1,
        )
        parser.add_argument(
            "--transaction-id",
            help="The ID value to use for the first transaction",
            type=int,
            default=1,
        )
        parser.add_argument(
            "--envelope-id",
            help="The ID value to use for the envelope",
            type=int,
            default=1,
        )
        parser.add_argument(
            "--output", help="The filename to output to.", type=str, default="out.xml"
        )

    def handle(self, *args, **options):
        username = settings.DATA_IMPORT_USERNAME
        try:
            author = User.objects.get(username=username)
        except User.DoesNotExist:
            sys.exit(
                f"Author does not exist, create user '{username}'"
                " or edit settings.DATA_IMPORT_USERNAME"
            )
        workbasket, _ = WorkBasket.objects.get_or_create(
            title=f"Update Commodity Codes",
            author=author,
            status=WorkflowStatus.PUBLISHED,
        )
        workbook = xlrd.open_workbook(options["spreadsheet"])
        cc_operations = workbook.sheet_by_name("cc_operations")
        cc_measures = workbook.sheet_by_name("cc_measures")

        cc_operations = cc_operations.get_rows()
        cc_measures = cc_measures.get_rows()

        for _ in range(1):
            next(cc_operations)
            next(cc_measures)

        mc = MeasureCreatingPatternWithExpression(
            duty_sentence_parser=None,
            generating_regulation=None,
            workbasket=workbasket,
            measure_sid_counter=counter_generator(options["measure_sid"]),
            measure_condition_sid_counter=counter_generator(
                options["measure_condition_sid"]
            )
        )
        me = MeasureEndingPattern(
            workbasket=workbasket,
        )
        with open(options["output"], mode="wb") as output:
            with EnvelopeSerializer(
                output,
                envelope_id=options["envelope_id"],
                transaction_counter=counter_generator(options["transaction_id"]),
                message_counter=counter_generator(start=1),
                max_envelope_size_in_mb=30,
            ) as env:
                try:
                    with django.db.transaction.atomic():
                            for transaction in self.create_transactions(
                                    mc,
                                    me,
                                    cc_operations,
                                    cc_measures,
                                    workbasket
                            ):
                                for model in transaction:
                                    #model.save()
                                    pass
                                env.render_transaction(transaction)
                finally:
                    django.db.transaction.rollback()

    def end_measures(self, measure_ender, measures, end_date, type):
        for old_row in measures:
            if type == UpdateType.UPDATE:
                new_start_date = end_date + timedelta(days=1)
            if type == UpdateType.DELETE:
                new_start_date = old_row.measure_start_date - timedelta(days=1) # to trigger delete instead of enddate
            yield list(
                measure_ender.end_date_measure(
                    old_row=old_row,
                    terminating_regulation=Regulation.objects.as_at(BREXIT).get(
                        regulation_id=old_row.regulation_id,
                        role_type=old_row.regulation_role,
                        approved=True,
                    ),
                    new_start_date=new_start_date
                )
            )

    duplicate_detection = defaultdict(lambda: defaultdict(list))

    def check_duplicate_measures(self, row, new_goods_nomenclature):
        unique_key = f'{row.measure_type}|{row.geo_id}|{row.additional_code_sid}'
        date_range = DateTimeTZRange(row.measure_start_date, row.real_end_date)
        unique_values = f'{row.conditions}|{row.duty_expression}|{row.excluded_geo_areas}|{row.measure_start_date}|{row.real_end_date}|{row.footnotes}'
        existing_unique_keys = self.duplicate_detection[new_goods_nomenclature.sid]
        # check if measure type, geo sid and add code transferred before
        if unique_key in existing_unique_keys:
            for existing_key_range, existing_key_value in existing_unique_keys[unique_key]:
                #  check if measure overlap in time with already transferred measures
                if (existing_key_range.upper is None or date_range.lower <= existing_key_range.upper) \
                        and (date_range.upper is None or date_range.upper >= existing_key_range.lower):
                    logger.debug(
                        f'duplicate measure found: sid ({new_goods_nomenclature.sid}), key ({unique_key}), value {unique_values}'
                    )
                    # check if we have conflicting values or exact duplicate
                    if existing_key_value != unique_values:
                        logger.debug(
                            f'conflicting measure: sid ({new_goods_nomenclature.sid}), key ({unique_key}, '
                            f'already transferred values {existing_key_value}, new values {unique_values}'
                        )
                        raise ValueError('Conflicting measures')
                    return True
        else:
            self.duplicate_detection[new_goods_nomenclature.sid][unique_key].append((date_range, unique_values))
        return False

    def transfer_measures(self, measure_creator, measures, new_goods_nomenclature):
        for row in measures:
            if self.check_duplicate_measures(row, new_goods_nomenclature):
                continue
            parsed_duty_condition_expressions = parse_duty_parts(row.duty_condition_parts, EUR_GBP_CONVERSION_RATE) \
                if row.duty_condition_parts else []
            parsed_duty_component = parse_duty_parts(row.duty_component_parts, EUR_GBP_CONVERSION_RATE) \
                if row.duty_component_parts else []
            footnote_ids = set(row.footnotes)
            footnotes = []
            for f in footnote_ids:
                footnotes.append(
                    Footnote.objects.get(
                        footnote_id=f[2:], footnote_type__footnote_type_id=f[0:2]
                    )
                )
            excluded_geo_areas = []
            for area in row.excluded_geo_areas:
                excluded_geo_areas.append(
                    GeographicalArea.objects.as_at(BREXIT).get(
                        sid=area,
                    )
                )
            if (
                    new_goods_nomenclature.valid_between.upper is None or
                    row.measure_start_date <= new_goods_nomenclature.valid_between.upper
            ) and (
                    row.measure_end_date is None or
                    row.measure_end_date >= new_goods_nomenclature.valid_between.lower.replace(tzinfo=None)
            ):
                yield list(
                    measure_creator.create(
                        geography=GeographicalArea.objects.as_at(BREXIT).get(
                            sid=row.geo_sid,
                        ),
                        goods_nomenclature=new_goods_nomenclature,
                        new_measure_type=MeasureType.objects.get(sid=row.measure_type),
                        geo_exclusion_list=excluded_geo_areas,
                        validity_start=max(new_goods_nomenclature.valid_between.lower.replace(tzinfo=None), row.measure_start_date),
                        validity_end=min(new_goods_nomenclature.valid_between.upper.replace(tzinfo=None), row.measure_end_date) if row.measure_end_date and new_goods_nomenclature.valid_between.upper else row.measure_end_date,
                        footnotes=footnotes,
                        duty_condition_expressions=parsed_duty_condition_expressions,
                        measure_components=parsed_duty_component,
                        additional_code=row.additional_code,
                        generating_regulation=Regulation.objects.get(
                            regulation_id=row.regulation_id,
                            role_type=row.regulation_role,
                            approved=True,
                        ),
                    )
                )

    def create_transactions(self, measure_creator, measure_ender, cc_operations, cc_measures, workbasket):

        # measure map
        cc_measure_groups = defaultdict(list)
        for row in cc_measures:
            cc_measure_row = OldMeasureRow(row)
            cc_measure_groups[cc_measure_row.goods_nomenclature_sid].append(cc_measure_row)

        # group operations together by cc
        cc_operation_groups = defaultdict(list)
        counter, previous_sid = 0, None
        for row in cc_operations:
            cc_operation_row = CCOperationRow(row)
            sid = cc_operation_row.goods_nomenclature_sid
            if sid != previous_sid:
                counter += 1
            key = f'{counter}|{cc_operation_row.goods_nomenclature_sid}'
            cc_operation_groups[key].append(cc_operation_row)
            previous_sid = cc_operation_row.goods_nomenclature_sid

        # process groups
        transfer_queue = defaultdict(list)     # old_gn:list(new_gn)
        for _, operations in cc_operation_groups.items():
            transaction = []
            for operation in operations:
                gn = None
                if operation.type == OperationType.GN:
                    # if we update the date of a GN we need to update the measures as well
                    if operation.update_type == UpdateType.UPDATE or \
                            operation.update_type == UpdateType.DELETE:
                        gn = GoodsNomenclature.objects.get(
                            sid=operation.goods_nomenclature_sid,
                        )
                        if (
                                operation.gn_validity_end_date is not None
                                or operation.update_type == UpdateType.DELETE
                        ) and operation.goods_nomenclature_sid in cc_measure_groups:
                            logger.debug(
                                f'ending {len(cc_measure_groups[gn.sid])} '
                                f'measures for {gn.item_id}'
                            )
                            yield from self.end_measures(
                                measure_ender,
                                cc_measure_groups[operation.goods_nomenclature_sid],
                                end_date=operation.gn_validity_end_date,
                                type=operation.update_type
                            )

                    gn, _ = GoodsNomenclature.objects.update_or_create(
                        sid=operation.goods_nomenclature_sid,
                        defaults={
                            'item_id': operation.goods_nomenclature_item_id,
                            'suffix': operation.productline_suffix,
                            'statistical': operation.statistical_indicator,
                            'valid_between': DateTimeTZRange(
                                operation.gn_validity_start_date,
                                operation.gn_validity_end_date,
                            ),
                            'workbasket': workbasket,
                            'update_type': operation.update_type,
                        }
                    )
                    logger.debug(
                        f'{"update" if operation.update_type == UpdateType.UPDATE else "create" if operation.update_type == UpdateType.CREATE else "delete"} '
                        f'commodity code {gn.item_id}: validity ({gn.valid_between}), '
                        f'suffix ({gn.suffix}), stat ({gn.statistical}), indicator({gn.statistical})'
                    )
                    transaction.append(gn)

                if operation.type == OperationType.INDENT:
                    gn = gn or GoodsNomenclature.objects.get(
                        sid=operation.goods_nomenclature_sid,
                    )
                    gn_indent = GoodsNomenclatureIndent(
                        sid=operation.goods_nomenclature_indent_sid,
                        indent=operation.number_indents,
                        indented_goods_nomenclature=gn,
                        valid_between=DateTimeTZRange(
                            operation.indent_validity_start_date,
                            None
                        ),
                        workbasket=workbasket,
                        update_type=operation.update_type,
                    )
                    logger.debug(
                        f'{"update" if operation.update_type == UpdateType.UPDATE else "create" if operation.update_type == UpdateType.CREATE else "delete"} '
                        f'indent for {gn.item_id}: indent ({gn_indent.indent}), validity ({gn_indent.valid_between})'
                    )
                    transaction.append(gn_indent)
                if operation.type == OperationType.DESCRIPTION:
                    gn = gn or GoodsNomenclature.objects.get(
                        sid=operation.goods_nomenclature_sid,
                    )
                    gn_description = GoodsNomenclatureDescription(
                        sid=operation.goods_nomenclature_description_period_sid,
                        description=operation.description,
                        valid_between=DateTimeTZRange(
                            operation.desc_validity_start_date,
                            None
                        ),
                        described_goods_nomenclature=gn,
                        workbasket=workbasket,
                        update_type=operation.update_type,
                    )
                    logger.debug(
                        f'{"update" if operation.update_type == UpdateType.UPDATE else "create" if operation.update_type == UpdateType.CREATE else "delete"} '
                        f'description for {gn.item_id}: {operation.description}'
                    )
                    transaction.append(gn_description)
                if operation.type == OperationType.ORIGIN:
                    gn = gn or GoodsNomenclature.objects.get(
                        sid=operation.goods_nomenclature_sid,
                    )
                    gn_derived_from = GoodsNomenclature.objects.get(
                        sid=operation.derived_goods_nomenclature_sid,
                    )
                    if operation.measure_transfer_candidate \
                            and operation.derived_goods_nomenclature_sid in cc_measure_groups:
                        transfer_queue[gn_derived_from].append(gn)

                    gn_origin = GoodsNomenclatureOrigin(
                        new_goods_nomenclature=gn,
                        derived_from_goods_nomenclature=gn_derived_from,
                        workbasket=workbasket,
                        update_type=operation.update_type,
                    )
                    logger.debug(
                        f'{"update" if operation.update_type == UpdateType.UPDATE else "create" if operation.update_type == UpdateType.CREATE else "delete"} '
                        f'origin: derived from ({gn_origin.new_goods_nomenclature.item_id}), '
                        f'new ({gn_origin.derived_from_goods_nomenclature.item_id})'
                    )
                    transaction.append(gn_origin)

                if operation.type == OperationType.FOOTNOTE:
                    gn = gn or GoodsNomenclature.objects.get(
                        sid=operation.goods_nomenclature_sid,
                    )
                    gn_footnote = FootnoteAssociationGoodsNomenclature(
                        goods_nomenclature=gn,
                        associated_footnote=Footnote.objects.get(
                            footnote_id=operation.footnote_id, footnote_type__footnote_type_id=operation.footnote_type
                        ),
                        valid_between=DateTimeTZRange(
                            operation.fn_validity_start_date,
                            operation.fn_validity_end_date
                        ),
                        workbasket=workbasket,
                        update_type=operation.update_type,
                    )
                    logger.debug(
                        f'{"update" if operation.update_type == UpdateType.UPDATE else "create" if operation.update_type == UpdateType.CREATE else "delete"} '
                        f'footnote association for {gn.item_id}: '
                        f'footnote ({operation.footnote_type}{operation.footnote_id}), validity ({gn_footnote.valid_between})'
                    )
                    transaction.append(gn_footnote)

                if operation.type == OperationType.SUCCESSOR:
                    gn_successor = GoodsNomenclatureSuccessor(
                        replaced_goods_nomenclature=GoodsNomenclature.objects.get(
                            sid=operation.goods_nomenclature_sid
                        ),
                        absorbed_into_goods_nomenclature=GoodsNomenclature.objects.get(
                            sid=operation.absorbed_goods_nomenclature_sid
                        ),
                        workbasket=workbasket,
                        update_type=operation.update_type,

                    )
                    logger.debug(
                        f'{"update" if operation.update_type == UpdateType.UPDATE else "create" if operation.update_type == UpdateType.CREATE else "delete"} '
                        f'successor: replaced ({gn_successor.replaced_goods_nomenclature.item_id})'
                        f', absorbed ({gn_successor.absorbed_into_goods_nomenclature.item_id})'
                    )
                    transaction.append(gn_successor)

            yield transaction

        # When all GN measures are end-dated we can transfer them to the new CCs if required
        for gn in transfer_queue.keys():
            for new_gn in transfer_queue[gn]:
                logger.debug(
                    f'transfer {len(cc_measure_groups[gn.sid])} '
                    f'measures from {gn.item_id} to {new_gn.item_id}'
                )
                yield from self.transfer_measures(
                    measure_creator,
                    measures=cc_measure_groups[gn.sid],
                    new_goods_nomenclature=new_gn
                )
