# Some measures were accidently deleted when cleaning up EU measures
# This script restores those measures as they were before the clean up
import json
import logging
import sys
from datetime import timedelta, datetime
from itertools import tee
from typing import List

import django
import xlrd
from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db.models.functions import Lower
from psycopg2._range import DateTimeTZRange
from xlrd.sheet import Cell

from additional_codes.models import AdditionalCodeDescription, AdditionalCode, AdditionalCodeType
from certificates.models import CertificateType, Certificate, CertificateDescription
from commodities.models import GoodsNomenclature, GoodsNomenclatureIndent, GoodsNomenclatureDescription, \
    GoodsNomenclatureOrigin, GoodsNomenclatureSuccessor
from common.models import Transaction
from common.renderers import counter_generator
from common.validators import UpdateType, ApplicabilityCode
from footnotes.models import Footnote, FootnoteType, FootnoteDescription
from footnotes.validators import ApplicationCode
from geo_areas.models import GeographicalArea
from geo_areas.validators import AreaCode
from importer.management.commands import update_commodity_codes
from importer.management.commands.import_reliefs import EUR_GBP_CONVERSION_RATE
from importer.management.commands.patterns import BREXIT, MeasureCreatingPatternWithExpression, OldMeasureRow, \
    MeasureEndingPattern, parse_date, parse_list
from importer.management.commands.utils import EnvelopeSerializer, parse_duty_parts, update_geo_area_description, \
    terminate_geo_area_members, add_geo_area_members, create_geo_area, blank
from measures.models import MeasureType, Measure, MeasurementUnit, FootnoteAssociationMeasure, \
    AdditionalCodeTypeMeasureType
from quotas.models import QuotaDefinition, QuotaOrderNumberOrigin, QuotaOrderNumber, QuotaOrderNumberOriginExclusion, \
    QuotaAssociation, QuotaBlocking, QuotaSuspension
from quotas.validators import QuotaCategory, AdministrationMechanism
from regulations.models import Regulation, Group
from regulations.validators import RoleType
from workbaskets.models import WorkBasket
from workbaskets.validators import WorkflowStatus

logger = logging.getLogger(__name__)

BREXIT_TO_INFINITY = DateTimeTZRange(BREXIT, None)


class CCRow:
    def __init__(self, old_row: List[Cell]) -> None:
        self.goods_nomenclature_sid = str(old_row[1].value)
        self.goods_nomenclature_item_id = str(old_row[2].value)
        self.producline_suffix = str(old_row[3].value)
        self.gn_validity_start_date = parse_date(old_row[4])
        self.gn_validity_end_date = parse_date(old_row[5])
        self.statistical_indicator = int(old_row[6].value)
        self.goods_nomenclature_indent_sid = str(old_row[7].value)
        self.indent_validity_start_date = parse_date(old_row[8])
        self.number_indents = int(old_row[9].value)
        self.description = str(old_row[10].value)
        self.goods_nomenclature_description_period_sid = str(old_row[11].value)
        self.desc_validity_start_date = parse_date(old_row[12])
        self.derived_goods_nomenclature_item_id = str(old_row[13].value)
        self.derived_productline_suffix = str(old_row[14].value)
        self.absorbed_goods_nomenclature_item_id = str(old_row[15].value)
        self.absorbed_productline_suffix = str(old_row[16].value)


class Command(BaseCommand):
    help = ""

    def add_arguments(self, parser):
        parser.add_argument(
            "spreadsheet",
            help="The XLSX file containing measures to be parsed.",
            type=str,
            default=None,
        )
        parser.add_argument(
            "ticket",
            help="The JIRA ticket ID",
            type=str,
        )
        parser.add_argument(
            "--measure-sid",
            help="The SID value to use for the first new measure",
            type=int,
        )
        parser.add_argument(
            "--measure-condition-sid",
            help="The SID value to use for the first new measure condition",
            type=int,
        )
        parser.add_argument(
            "--group_area_sid",
            help="The SID value to use for the first new group area",
            type=int,
        )
        parser.add_argument(
            "--group_area_description_sid",
            help="The SID value to use for the first new group area description",
            type=int,
        )
        parser.add_argument(
            "--footnote_description_sid",
            help="The SID value to use for the first new footnote description",
            type=int,
        )
        parser.add_argument(
            "--goodsnomenclature_description_sid",
            help="The SID value to use for the first new cc description",
            type=int,
        )
        parser.add_argument(
            "--order_number_sid",
            help="The SID value to use for the first new cc description",
            type=int,
        )
        parser.add_argument(
            "--quota_definition_sid",
            help="The SID value to use for the first new cc description",
            type=int,
        )
        parser.add_argument(
            "--order_number_origin_sid",
            help="The SID value to use for the first new cc description",
            type=int,
        )
        parser.add_argument(
            "--certificate_description_sid",
            help="The SID value to use for the first new cc description",
            type=int,
        )
        parser.add_argument(
            "--additional_code_sid",
            help="The SID value to use for the first new additional code",
            type=int,
        )
        parser.add_argument(
            "--additional_code_description_period_sid",
            help="The SID value to use for the first new additional code description",
            type=int,
        )
        parser.add_argument(
            "--transaction-id",
            help="The ID value to use for the first transaction",
            type=int,
        )
        parser.add_argument(
            "--envelope-id",
            help="The ID value to use for the envelope",
            type=int,
        )
        parser.add_argument(
            "--output", help="The filename to output to.", type=str, default="out.xml"
        )

    def handle(self, *args, **options):
        with django.db.transaction.atomic():
            username = settings.DATA_IMPORT_USERNAME
            try:
                author = User.objects.get(username=username)
            except User.DoesNotExist:
                sys.exit(
                    f"Author does not exist, create user '{username}'"
                    " or edit settings.DATA_IMPORT_USERNAME"
                )
            workbasket, _ = WorkBasket.objects.get_or_create(
                title=f"Update Measures",
                author=author,
                status=WorkflowStatus.PUBLISHED,
            )
            transaction_model, _ = Transaction.objects.get_or_create(workbasket=workbasket, order=1)
            workbook = xlrd.open_workbook(options["spreadsheet"]) if options["spreadsheet"] else None
            mc = MeasureCreatingPatternWithExpression(
                duty_sentence_parser=None,
                generating_regulation=None,
                transaction=transaction_model,
                measure_sid_counter=counter_generator(options["measure_sid"]),
                measure_condition_sid_counter=counter_generator(
                    options["measure_condition_sid"]
                )
            )
            me = MeasureEndingPattern(
                transaction=transaction_model,
            )

            counters = {
                "group_area_description_sid_counter": counter_generator(
                    options["group_area_description_sid"]
                ),
                "group_area_sid_counter": counter_generator(
                    options["group_area_sid"]
                ),
                "footnote_description_sid_counter": counter_generator(
                    options["footnote_description_sid"]
                ),
                "goodsnomenclature_description_sid_counter": counter_generator(
                    options["goodsnomenclature_description_sid"]
                ),
                "quota_definition_sid_counter": counter_generator(
                    options["quota_definition_sid"]
                ),
                "order_number_sid_counter": counter_generator(
                    options["order_number_sid"]
                ),
                "order_number_origin_sid_counter": counter_generator(
                    options["order_number_origin_sid"]
                ),
                "certificate_description_sid_counter": counter_generator(
                    options["certificate_description_sid"]
                ),
                "additional_code_sid_counter": counter_generator(
                    options["additional_code_sid"]
                ),
                "additional_code_description_period_sid_counter": counter_generator(
                    options["additional_code_description_period_sid"]
                ),
            }

            with open(options["output"], mode="wb") as output:
                with EnvelopeSerializer(
                    output,
                    envelope_id=options["envelope_id"],
                    transaction_counter=counter_generator(options["transaction_id"]),
                    message_counter=counter_generator(start=1),
                    max_envelope_size_in_mb=30,
                ) as env:
                    for ticket in options["ticket"].split(","):
                        try:
                            sheet_names = workbook.sheet_names()
                            data = {}
                            for name in sheet_names:
                                parts = name.split('-')
                                logger.debug(parts)
                                name_prefix = parts[0] + '-' + ''.join(filter(str.isdigit, parts[1]))
                                if name_prefix == ticket and 'info' not in name:
                                    sheet = workbook.sheet_by_name(name)
                                    rows = sheet.get_rows()
                                    logger.debug(name)
                                    for _ in range(1):
                                        next(rows)
                                    data[name] = rows
                        except xlrd.biffh.XLRDError:
                            sheet = None
                        function = f'create_transactions_{ticket.replace("-","")}'
                        for transaction in getattr(self, function)(
                                mc,
                                me,
                                list(data.values())[0] if len(data.keys()) == 1 else data,
                                transaction_model,
                                counters
                        ):
                            for model in transaction:
                                #model.save(force_write=True)
                                pass
                            env.render_transaction(transaction)

            django.db.transaction.set_rollback(True)

    def process_measure_sheet(self, measure_creator, measure_ender, existing_measures, new_start_date=BREXIT, update=False, raw=False):
        rows = existing_measures if raw else (OldMeasureRow(row) for row in existing_measures)
        for row in rows:
            if row.measure_sid and not update:
                yield list(
                    measure_ender.end_date_measure(
                        old_row=row,
                        terminating_regulation=Regulation.objects.get(
                            regulation_id=row.regulation_id,
                            role_type=row.regulation_role,
                            approved=True,
                        ),
                        new_start_date=new_start_date
                    )
                )
            else:
                parsed_duty_condition_expressions = parse_duty_parts(row.duty_condition_parts, EUR_GBP_CONVERSION_RATE) \
                    if row.duty_condition_parts else []
                parsed_duty_component = parse_duty_parts(row.duty_component_parts, EUR_GBP_CONVERSION_RATE) \
                    if row.duty_component_parts else []
                footnote_ids = set(row.footnotes)
                footnotes = []
                for f in footnote_ids:
                    logger.debug(f'{f[2:]}/{f[0:2]}')
                    footnotes.append(
                        Footnote.objects.current().get(
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
                if row.measure_sid and update:
                    yield [Measure(
                        sid=row.measure_sid,
                        measure_type=MeasureType.objects.get(
                            sid=row.measure_type
                        ),
                        geographical_area=GeographicalArea.objects.current().get(
                            sid=row.geo_sid,
                        ),
                        goods_nomenclature=row.goods_nomenclature,
                        valid_between=DateTimeTZRange(
                            row.measure_start_date,
                            row.measure_end_date
                        ),
                        generating_regulation=Regulation.objects.get(
                            regulation_id=row.regulation_id,
                            role_type=row.regulation_role,
                            approved=True,
                        ),
                        terminating_regulation=Regulation.objects.get(
                            regulation_id=row.justification_regulation_id,
                            role_type=row.justification_regulation_role,
                            approved=True,
                        ) if row.justification_regulation_id else None,
                        order_number=QuotaOrderNumber.objects.current().get(
                            order_number=row.order_number,
                            valid_between__contains=DateTimeTZRange(
                                lower=row.measure_start_date,
                                upper=row.measure_end_date,
                            ),
                        ) if row.order_number else None,
                        additional_code=AdditionalCode.objects.current().get(
                            sid=row.additional_code_sid
                        ) if row.additional_code_sid else None,
                        update_type=UpdateType.UPDATE,
                        transaction=measure_creator.transaction,
                    )]
                else:
                    yield list(
                        measure_creator.create(
                            geography=GeographicalArea.objects.current().get(
                                sid=row.geo_sid,
                            ),
                            goods_nomenclature=row.goods_nomenclature,
                            new_measure_type=MeasureType.objects.current().get(sid=row.measure_type),
                            geo_exclusion_list=excluded_geo_areas,
                            validity_start=row.measure_start_date,
                            validity_end=row.measure_end_date,
                            footnotes=footnotes,
                            order_number=QuotaOrderNumber.objects.current().get(
                                order_number=row.order_number,
                            ) if row.order_number else None,
                            duty_condition_expressions=parsed_duty_condition_expressions,
                            measure_components=parsed_duty_component,
                            additional_code=AdditionalCode.objects.current().get(
                                sid=row.additional_code_sid
                            ) if row.additional_code_sid else None,
                            generating_regulation=Regulation.objects.get(
                                regulation_id=row.regulation_id,
                                role_type=row.regulation_role,
                                approved=True,
                            ),
                        )
                    )

    def create_transactions_cert9(self, measure_creator, measure_ender, existing_measures, transaction, counters):
        type = CertificateType(
            sid=9,
            valid_between=DateTimeTZRange(
                datetime(1970, 1, 1),
                None
            ),
            description='National Document',
            transaction=transaction,
            update_type=UpdateType.CREATE
        )
        transactions = [type]

        sids = [
            '001',
            '002',
            '003',
            '004',
            '100',
            '101',
            '102',
            '103',
            '104',
            '105',
            '106',
            '107',
            '108',
            '111',
            '112',
            '113',
            '114',
            '115',
            '116',
            '118',
            '119',
            '120',
            '200',
            '300',
            '578',
            'AID',
            'AIE',
            'AIV',
            'CLM',
            'DCR',
            'DCS',
            'ING',
            'MCR',
            'RCP',
            'SDC',
            'WKS',
        ]

        for sid in sids:
            transactions.append(Certificate(
                sid=sid,
                valid_between=DateTimeTZRange(
                    datetime(1971, 12, 31),
                    None
                ),
                certificate_type=type,
                transaction=transaction,
                update_type=UpdateType.CREATE
            ))
        yield transactions

    def create_transactions_topscert9desc(self, measure_creator, measure_ender, cert_desc, transaction, counters):
        type = CertificateType.objects.current().get(
            sid=9,
        )
        for row in cert_desc:
            logger.debug(row)
            certificate_description_period_sid = str(row[0].value)
            certificate_code = str(row[2].value)
            validity_start_date = parse_date(row[3])
            description = str(row[4].value)

            certificate_description = CertificateDescription.objects.create(
                sid=certificate_description_period_sid,
                described_certificate=Certificate.objects.current().get(
                    sid=certificate_code,
                    certificate_type=type,
                ),
                description=description,
                valid_between=DateTimeTZRange(
                    validity_start_date,
                    None
                ),
                transaction=transaction,
                update_type=UpdateType.CREATE,
            )
            yield [certificate_description]

    def create_transactions_tops1(self, measure_creator, measure_ender, existing_measures, transaction, counters):
        # update GEO areas
        yield list(update_geo_area_description(
            valid_between=BREXIT_TO_INFINITY,
            transaction=transaction,
            group_area_sid=217,
            old_area_description_sid=1332,
            new_area_description_sid=counters['group_area_description_sid_counter'](),
            description="GSP – General Framework",
        ))
        yield list(update_geo_area_description(
            valid_between=BREXIT_TO_INFINITY,
            transaction=transaction,
            group_area_sid=62,
            old_area_description_sid=1333,
            new_area_description_sid=counters['group_area_description_sid_counter'](),
            description="GSP – Least Developed Countries",
        ))
        yield list(update_geo_area_description(
            valid_between=BREXIT_TO_INFINITY,
            transaction=transaction,
            group_area_sid=51,
            old_area_description_sid=1334,
            new_area_description_sid=counters['group_area_description_sid_counter'](),
            description="GSP – Enhanced Framework",
        ))
        yield list(add_geo_area_members(
            valid_between=BREXIT_TO_INFINITY,
            transaction=transaction,
            group_area=217,
            member_area_sids=[
                444,    # Jordan
            ],
        ))
        yield list(terminate_geo_area_members(
            end_date=BREXIT - timedelta(days=1),
            transaction=transaction,
            group_area_sid=217,
            member_area_sids=[
                260,    # Cameroon
                279,    # Moldova
            ],
            delete=True
        ))
        yield from self.process_measure_sheet(measure_creator, measure_ender, existing_measures)

    def create_transactions_tops12(self, measure_creator, measure_ender, existing_measures, transaction, counters):
        for old_row in (OldMeasureRow(row) for row in existing_measures):
            parsed_duty_condition_expressions = parse_duty_parts(old_row.duty_condition_parts, EUR_GBP_CONVERSION_RATE) \
                if old_row.duty_condition_parts else []
            parsed_duty_component = parse_duty_parts(old_row.duty_component_parts, EUR_GBP_CONVERSION_RATE) \
                if old_row.duty_component_parts else []
            footnote_ids = set(old_row.footnotes)
            footnotes = [
                Footnote.objects.as_at(BREXIT).get(
                    footnote_id=f[2:], footnote_type__footnote_type_id=f[0:2]
                )
                for f in footnote_ids
            ]
            yield list(
                measure_creator.create(
                    geography=GeographicalArea.objects.as_at(BREXIT).get(
                        sid=old_row.geo_sid,
                    ),
                    goods_nomenclature=old_row.goods_nomenclature,
                    new_measure_type=MeasureType.objects.get(sid=old_row.measure_type),
                    validity_start=BREXIT,
                    footnotes=footnotes,
                    duty_condition_expressions=parsed_duty_condition_expressions,
                    measure_components=parsed_duty_component,
                    additional_code=old_row.additional_code,
                    generating_regulation=Regulation.objects.get(
                        regulation_id=old_row.regulation_id,
                        role_type=old_row.regulation_role,
                        approved=True,
                    ),
                )
            )

    def create_transactions_tops22(self, measure_creator, measure_ender, existing_measures, transaction, counters):
        yield from self.process_measure_sheet(measure_creator, measure_ender, existing_measures)

    def create_transactions_tops43(self, measure_creator, measure_ender, existing_measures, transaction, counters):
        yield from self.process_measure_sheet(measure_creator, measure_ender, existing_measures)

    def create_transactions_tops32(self, measure_creator, measure_ender, existing_measures, transaction, counters):
        params = {
            'regulation_group': Group.objects.get(group_id='MLA'),
            'published_at': datetime(2009, 4, 22),
            'approved': True,
            'valid_between': DateTimeTZRange(BREXIT, None),
            'information_text': 'The Cat and Dog Fur (Control of Import, Export and Placing on the Market) (Amendment) Regulations 2009',
            'public_identifier': 'S.I. 2009/1056',
            'url': 'https://www.legislation.gov.uk/uksi/2009/1056'
        }
        generating_regulation = Regulation.objects.create(
            regulation_id='X0910560',
            role_type=RoleType.BASE,
            transaction=transaction,
            update_type=UpdateType.CREATE,
            **params,
        )
        yield [generating_regulation]
        params = {
            'regulation_group': Group.objects.get(group_id='PRS'),
            'published_at': datetime(2020, 11, 25),
            'approved': True,
            'valid_between': DateTimeTZRange(BREXIT, None),
            'information_text': 'The Prevention of Trade Diversion (Key Medicines) (EU Exit) Regulations 2020',
            'public_identifier': 'S.I. 2020/1354',
            'url': 'https://www.legislation.gov.uk/uksi/2020/1354'
        }
        generating_regulation = Regulation.objects.create(
            regulation_id='X2013540',
            role_type=RoleType.BASE,
            transaction=transaction,
            update_type=UpdateType.CREATE,
            **params,
        )
        yield [generating_regulation]
        params = {
            'regulation_group': Group.objects.get(group_id='PRS'),
            'published_at': datetime(2020, 12, 10),
            'approved': True,
            'valid_between': DateTimeTZRange(BREXIT, None),
            'information_text': 'The Trade in Torture etc. Goods (Amendment) (EU Exit) Regulations 2020',
            'public_identifier': 'S.I. 2020/1479',
            'url': 'https://www.legislation.gov.uk/uksi/2020/1479'
        }
        generating_regulation = Regulation.objects.create(
            regulation_id='X2014790',
            role_type=RoleType.BASE,
            transaction=transaction,
            update_type=UpdateType.CREATE,
            **params,
        )
        yield [generating_regulation]
        # members = [
        #     ('196', 'Afghanistan'),
        #     ('448', 'Angola'),
        #     ('142', 'Armenia'),
        #     ('255', 'Azerbaijan'),
        #     ('432', 'Bangladesh'),
        #     ('202', 'Benin'),
        #     ('434', 'Bhutan'),
        #     ('96', 'Botswana'),
        #     ('380', 'Burkina Faso'),
        #     ('381', 'Burundi'),
        #     ('389', 'Cabo Verde'),
        #     ('336', 'Cambodia'),
        #     ('260', 'Cameroon'),
        #     ('435', 'Central African Republic'),
        #     ('203', 'Chad'),
        #     ('338', 'Comoros'),
        #     ('436', 'Congo'),
        #     ('295', 'Congo (Democratic Republic)'),
        #     ('207', 'Djibouti'),
        #     ('443', 'Equatorial Guinea'),
        #     ('121', 'Eritrea'),
        #     ('149', 'Ethiopia'),
        #     ('50', 'Gambia'),
        #     ('211', 'Ghana'),
        #     ('112', 'Guinea'),
        #     ('394', 'Guinea-Bissau'),
        #     ('396', 'Haiti'),
        #     ('268', 'Honduras'),
        #     ('154', 'India'),
        #     ('214', 'Indonesia'),
        #     ('385', 'Ivory Coast'),
        #     ('157', 'Kenya'),
        #     ('337', 'Kiribati'),
        #     ('272', 'Kyrgyzstan'),
        #     ('116', 'Laos'),
        #     ('402', 'Lesotho'),
        #     ('278', 'Liberia'),
        #     ('341', 'Madagascar'),
        #     ('281', 'Malawi'),
        #     ('223', 'Maldives'),
        #     ('160', 'Mali'),
        #     ('280', 'Mauritania'),
        #     ('279', 'Moldova'),
        #     ('161', 'Mongolia'),
        #     ('283', 'Mozambique'),
        #     ('239', 'Myanmar (Burma)'),
        #     ('284', 'Namibia'),
        #     ('311', 'Nepal'),
        #     ('374', 'Nicaragua'),
        #     ('119', 'Niger'),
        #     ('162', 'Nigeria'),
        #     ('115', 'North Korea'),
        #     ('89', 'Pakistan'),
        #     ('38', 'Rwanda'),
        #     ('327', 'Samoa'),
        #     ('433', 'Sao Tome and Principe'),
        #     ('257', 'Senegal'),
        #     ('41', 'Sierra Leone'),
        #     ('379', 'Solomon Islands'),
        #     ('383', 'Somalia'),
        #     ('442', 'South Africa'),
        #     ('201', 'Sudan'),
        #     ('76', 'Swaziland'),
        #     ('438', 'Tajikistan'),
        #     ('387', 'Tanzania'),
        #     ('67', 'Timor-Leste'),
        #     ('204', 'Togo'),
        #     ('386', 'Tuvalu'),
        #     ('262', 'Uganda'),
        #     ('107', 'Vanuatu'),
        #     ('48', 'Yemen'),
        #     ('151', 'Zambia'),
        #     ('333', 'Zimbabwe'),
        # ]
        # yield list(create_geo_area(
        #     valid_between=BREXIT_TO_INFINITY,
        #     transaction=transaction,
        #     description='Countries - Prevention of Trade Diversion (Key Medicines) S.I. 2020/1354',
        #     area_id='3200',
        #     area_sid=counters['group_area_sid_counter'](),
        #     area_description_sid=counters['group_area_description_sid_counter'](),
        #     type=AreaCode.GROUP,
        #     member_sids=[sid for sid, description in members],
        # ))
        new_footnote = Footnote.objects.create(
            footnote_type=FootnoteType.objects.current().get(
                footnote_type_id='TM'
            ),
            footnote_id='922',
            valid_between=BREXIT_TO_INFINITY,
            transaction=transaction,
            update_type=UpdateType.CREATE,
        )
        new_footnote_description = FootnoteDescription.objects.create(
            description_period_sid=counters["footnote_description_sid_counter"](),
            described_footnote=new_footnote,
            description='Import is prohibited for tiered-priced products falling under Amendment (EU Exit) 2020/1354 on the prevention of trade diversion (Key Medicines).',
            valid_between=BREXIT_TO_INFINITY,
            transaction=transaction,
            update_type=UpdateType.CREATE,
        )
        yield list([new_footnote, new_footnote_description])
        yield from self.process_measure_sheet(measure_creator, measure_ender, existing_measures)

    def create_transactions_tops24(self, measure_creator, measure_ender, existing_measures, transaction, counters):
        yield from self.process_measure_sheet(measure_creator, measure_ender, existing_measures)

    def create_transactions_tops25(self, measure_creator, measure_ender, existing_measures, transaction, counters):
        #add_code = AdditionalCode.objects.current().get(
        #    sid='14001'
        #)
        old_description = AdditionalCodeDescription.objects.current().get(
            description_period_sid='11001'
        )
        description = old_description.new_draft(workbasket=transaction.workbasket, save=False)
        description.description = 'Goods that are COVID-19 critical'
        description.transaction = transaction
        description.update_type = UpdateType.UPDATE
        yield [description]

    def create_transactions_tops53(self, measure_creator, measure_ender, cc_operations, transaction, counters):
        yield from update_commodity_codes.Command().create_transactions(
            measure_creator, measure_ender, cc_operations, [], transaction
        )

    def create_transactions_tops47(self, measure_creator, measure_ender, existing_measures, transaction, counters):
        yield from self.process_measure_sheet(
            measure_creator,
            measure_ender,
            existing_measures,
            new_start_date=datetime(2021, 1, 25)
        )

    def create_transactions_tops14(self, measure_creator, measure_ender, existing_measures, transaction, counters):
        yield from self.process_measure_sheet(
            measure_creator,
            measure_ender,
            existing_measures,
        )

    def create_transactions_tops54(self, measure_creator, measure_ender, existing_measures, transaction, counters):
        footnote = Footnote.objects.current().get(
            footnote_type=FootnoteType.objects.get(
                footnote_type_id='PR',
            ),
            footnote_id='011'
        )
        new_footnote_description = FootnoteDescription(
            description_period_sid=counters["footnote_description_sid_counter"](),
            described_footnote=footnote,
            description='Enquiries: plant.health@forestrycommission.gov.uk',
            valid_between=DateTimeTZRange(datetime(2021, 1, 29), None),
            transaction=transaction,
            update_type=UpdateType.CREATE,
        )
        yield [new_footnote_description]

    def create_transactions_tops48(self, measure_creator, measure_ender, existing_measures, transaction_model, counters):
        #ccs = GoodsNomenclatureDescription.objects.filter(
        #    description__icontains='€'
        #).order_by(Lower('valid_between'))
        mapping = {
            '€ 30': '25.00 GBP',
            '€ 18': '15.00 GBP',
            '€ 22': '18.00 GBP',
            '€ 7,9': '6.60 GBP',
            '€ 2': '1.60 GBP',
            '€ 224': '187.00 GBP',
            '€ 35': '29.00 GBP',
            '€ 17,50': '14.00 GBP',
            '€ 65': '54.00 GBP',
            '€ 30': '25.00 GBP',
            '€ 18': '15.00 GBP',
            '€ 22': '18.00 GBP',
            '€ 7,9': '6.60 GBP',
            '€ 2': '1.60 GBP',
            '€ 224': '187.00 GBP',
            '€ 35': '29.00 GBP',
            '€ 17,50': '14.00 GBP',
            '€ 65': '54.00 GBP',
        }
        ccs = GoodsNomenclatureDescription.objects.raw(
            """
                select distinct on (t1.sid) t2.* from commodities_goodsnomenclature t1 
                left join commodities_goodsnomenclaturedescription t2 on t1.trackedmodel_ptr_id = t2.described_goods_nomenclature_id 
                where description like '%%€%%' and (upper(t1.valid_between) is null or upper(t1.valid_between) >= '2021-1-1') 
                order by t1.sid asc, lower(t2.valid_between) desc
            """
        )
        for cc in ccs:
            new_description = cc.description
            for old, new in mapping.items():
                new_description = new_description.replace(old, new)
            cc.description = new_description
            yield [GoodsNomenclatureDescription(
                described_goods_nomenclature=cc.described_goods_nomenclature,
                sid=counters["goodsnomenclature_description_sid_counter"](),
                description=new_description,
                valid_between=BREXIT_TO_INFINITY,
                transaction=transaction_model,
                update_type=UpdateType.CREATE
            )]

    def create_transactions_tops58(self, measure_creator, measure_ender, data, transaction_model,
                                   counters):
        cc_operations = data['tops-58a']
        cc_measures = data['tops-58b']
        new_measures = data['tops-58c']
        yield from update_commodity_codes.Command().create_transactions(
            measure_creator, measure_ender, cc_operations, cc_measures, transaction_model, auto_migrate=False
        )

        yield from self.process_measure_sheet(
            measure_creator,
            measure_ender,
            new_measures,
        )

    def create_transactions_tops36(self, measure_creator, measure_ender, existing_measures, transaction, counters):
        yield from self.process_measure_sheet(
            measure_creator,
            measure_ender,
            existing_measures,
        )

    def create_transactions_tops39(self, measure_creator, measure_ender, existing_measures, transaction, counters):
        for order_number in ('054729', '054730', '054731'):
            quota_order_number = QuotaOrderNumber(
                sid=counters['order_number_sid_counter'](),
                order_number=order_number,
                update_type=UpdateType.CREATE,
                transaction=transaction,
                mechanism=AdministrationMechanism.LICENSED,
                category=QuotaCategory.PREFERENTIAL,
                valid_between=BREXIT_TO_INFINITY,
            )
            quota_order_number.save()
            origin = QuotaOrderNumberOrigin(
                sid=counters['order_number_origin_sid_counter'](),
                order_number=quota_order_number,
                geographical_area=GeographicalArea.objects.current().get(
                    sid=392
                ),
                update_type=UpdateType.CREATE,
                transaction=transaction,
                valid_between=quota_order_number.valid_between,
            )
            origin.save()
            volume = 3356000 if order_number == '054729' else 5001000
            definition = QuotaDefinition(
                sid=counters['quota_definition_sid_counter'](),
                order_number=quota_order_number,
                initial_volume=volume,
                volume=volume,
                valid_between=DateTimeTZRange(
                    BREXIT,
                    datetime(2021, 12, 31)
                ),
                maximum_precision=3,
                quota_critical_threshold=90,
                measurement_unit=MeasurementUnit.objects.get(code="KGM"),
                update_type=UpdateType.CREATE,
                transaction=transaction,
            )
            definition.save()
            #yield [quota_order_number, origin, definition]

        cert_1 = Certificate(
            sid='031',
            valid_between=BREXIT_TO_INFINITY,
            certificate_type=CertificateType.objects.current().get(
                sid='A'
            ),
            transaction=transaction,
            update_type=UpdateType.CREATE
        )
        cert_1.save()
        cert_1_desc = CertificateDescription(
            sid=counters['certificate_description_sid_counter'](),
            description='Certificate of authenticity issued by Vietnamese authorities for quota number 054731.',
            described_certificate=cert_1,
            valid_between=BREXIT_TO_INFINITY,
            transaction=transaction,
            update_type=UpdateType.CREATE
        )
        yield [cert_1, cert_1_desc]

        new_footnote = Footnote.objects.create(
            footnote_type=FootnoteType.objects.current().get(
                footnote_type_id='CD'
            ),
            footnote_id='984',
            valid_between=BREXIT_TO_INFINITY,
            transaction=transaction,
            update_type=UpdateType.CREATE,
        )
        new_footnote_description = FootnoteDescription.objects.create(
            description_period_sid=counters["footnote_description_sid_counter"](),
            described_footnote=new_footnote,
            description='Vietnamese certificate of authenticity required to claim the duty preference.',
            valid_between=BREXIT_TO_INFINITY,
            transaction=transaction,
            update_type=UpdateType.CREATE,
        )
        yield [new_footnote, new_footnote_description]

        yield from self.process_measure_sheet(
            measure_creator,
            measure_ender,
            existing_measures,
        )

    def create_transactions_tops66(self, measure_creator, measure_ender, new_measures, transaction, counters):
        yield from self.process_measure_sheet(
            measure_creator,
            measure_ender,
            new_measures,
        )

    def create_transactions_tops68(self, measure_creator, measure_ender, new_measures, transaction, counters):
        order_number = '059179'
        quota_order_number = QuotaOrderNumber(
            sid=counters['order_number_sid_counter'](),
            order_number=order_number,
            update_type=UpdateType.CREATE,
            transaction=transaction,
            valid_between=BREXIT_TO_INFINITY,
            mechanism=AdministrationMechanism.FCFS,
            category=QuotaCategory.PREFERENTIAL,
        )
        quota_order_number.save()
        origin = QuotaOrderNumberOrigin(
            sid=counters['order_number_origin_sid_counter'](),
            order_number=quota_order_number,
            geographical_area=GeographicalArea.objects.current().get(
                sid=252
            ),
            update_type=UpdateType.CREATE,
            transaction=transaction,
            valid_between=quota_order_number.valid_between,
        )
        origin.save()
        definition1 = QuotaDefinition(
            sid=counters['quota_definition_sid_counter'](),
            order_number=quota_order_number,
            initial_volume=257000,
            volume=257000,
            valid_between=DateTimeTZRange(
                BREXIT,
                datetime(2021, 6, 30)
            ),
            maximum_precision=3,
            quota_critical_threshold=90,
            measurement_unit=MeasurementUnit.objects.get(code="KGM"),
            update_type=UpdateType.CREATE,
            transaction=transaction,
        )
        definition1.save()
        definition2 = QuotaDefinition(
            sid=counters['quota_definition_sid_counter'](),
            order_number=quota_order_number,
            initial_volume=256000,
            volume=256000,
            valid_between=DateTimeTZRange(
                datetime(2021, 7, 1),
                datetime(2021, 12, 31)
            ),
            maximum_precision=3,
            quota_critical_threshold=90,
            measurement_unit=MeasurementUnit.objects.get(code="KGM"),
            update_type=UpdateType.CREATE,
            transaction=transaction,
        )
        definition2.save()
        yield [quota_order_number, origin, definition1, definition2]

        yield from self.process_measure_sheet(
            measure_creator,
            measure_ender,
            new_measures,
        )

    def create_transactions_tops74(self, measure_creator, measure_ender, new_measures, transaction, counters):
        yield from self.process_measure_sheet(
            measure_creator,
            measure_ender,
            new_measures,
        )

    def create_transactions_tops73(self, measure_creator, measure_ender, new_measures, transaction, counters):
        new_footnote_description = FootnoteDescription.objects.current().get(
            description_period_sid=200400,
        )
        new_footnote_description.transaction = transaction
        new_footnote_description.update_type = UpdateType.UPDATE
        new_footnote_description.description = 'Application of regulation 13(2)(d) of the Trade Preference Scheme (EU Exit) Regulations 2020.'
        yield [new_footnote_description]

    def create_transactions_tops69(self, measure_creator, measure_ender, new_measures, transaction, counters):
        cert_1_desc = CertificateDescription(
            sid=counters['certificate_description_sid_counter'](),
            description='Certificate of conformity with the GB marketing standards for fresh fruit and vegetables',
            described_certificate=Certificate.objects.current().get(
                sid='002',
                certificate_type=CertificateType.objects.current().get(
                    sid='N'
                ),

            ),
            valid_between=BREXIT_TO_INFINITY,
            transaction=transaction,
            update_type=UpdateType.CREATE
        )
        yield [cert_1_desc]

        new_footnote_description = FootnoteDescription.objects.current().get(
            description_period_sid=200432,
        )
        new_footnote_description.transaction = transaction
        new_footnote_description.update_type = UpdateType.UPDATE
        new_footnote_description.description = 'Contact Details for lead Government Department are as follows: <P>HMI Admin Support,</P><P>(CIT), APHA, Defra, Foss House,</P><P>Kings Pool 1-2 Peasholme Green,</P><P>York, YO1 7PX</P><P>Tel: 0300 100 0313</P><P>Email: peachenquiries@apha.gov.uk</P>'
        yield [new_footnote_description]

        yield from self.process_measure_sheet(
            measure_creator,
            measure_ender,
            new_measures,
        )

    def create_transactions_tops81(self, measure_creator, measure_ender, data, transaction_model,
                                   counters):
        cc_operations = data['tops-81a']
        cc_measures = data['tops-81b']
        new_measures = data['tops-81c']
        yield from update_commodity_codes.Command().create_transactions(
            measure_creator, measure_ender, cc_operations, cc_measures, transaction_model, auto_migrate=False
        )

        yield from self.process_measure_sheet(
            measure_creator,
            measure_ender,
            new_measures,
        )

    def create_transactions_tops78(self, measure_creator, measure_ender, new_measures, transaction, counters):
        new_footnote_description = FootnoteDescription.objects.current().get(
            description_period_sid=200434,
        )
        new_footnote_description.transaction = transaction
        new_footnote_description.update_type = UpdateType.UPDATE
        new_footnote_description.description = 'A Controlled Drugs/Precursor Chemical import licence is only required where the item is being used in drugs manufacture. Any queries please contact: <P>Controlled Drugs/Precursor Chemical Import Licence,</P><P>Home Office Drug Licensing</P><P>PO BOX 2163</P><P>Croydon</P><P>CR90 9TA</P><P>Contact- dflu.ie@homeoffice.gov.uk</P><P>https://www.gov.uk/guidance/controlled-drugs-import-and-export-licences</P><P>Note: Applications for import licences must be made online for controlled drugs.</P>'
        yield [new_footnote_description]

    def create_transactions_tops77(self, measure_creator, measure_ender, new_measures, transaction, counters):
        yield from self.process_measure_sheet(
            measure_creator,
            measure_ender,
            new_measures,
        )

    def create_transactions_tops44(self, measure_creator, measure_ender, new_measures, transaction, counters):
        yield from self.process_measure_sheet(
            measure_creator,
            measure_ender,
            new_measures,
        )

    def create_transactions_tops44(self, measure_creator, measure_ender, new_measures, transaction, counters):
        yield from self.process_measure_sheet(
            measure_creator,
            measure_ender,
            new_measures,
        )

    def create_transactions_tops60(self, measure_creator, measure_ender, new_measures, transaction, counters):
        params = {
            'regulation_group': Group.objects.get(group_id='FTA'),
            'published_at': datetime(2021, 1, 1),
            'approved': True,
            'valid_between': DateTimeTZRange(BREXIT, None),
        }
        generating_regulation = Regulation.objects.create(
            regulation_id='C2100340',
            role_type=RoleType.BASE,
            transaction=transaction,
            update_type=UpdateType.CREATE,
            **params,
        )
        yield [generating_regulation]
        yield from self.process_measure_sheet(
            measure_creator,
            measure_ender,
            new_measures,
        )

    def create_transactions_tops49(self, measure_creator, measure_ender, new_measures, transaction, counters):
        cert_1_desc = CertificateDescription(
            sid=counters['certificate_description_sid_counter'](),
            description='Certificate concerning pelts of certain wild animal species and of goods incorporating such pelts subject to The Leghold Trap and Pelt Imports (Amendment etc.) (EU Exit) Regulations 2019 No 2019/16',
            described_certificate=Certificate.objects.current().get(
                sid='056',
                certificate_type=CertificateType.objects.current().get(
                    sid='C'
                ),

            ),
            valid_between=BREXIT_TO_INFINITY,
            transaction=transaction,
            update_type=UpdateType.CREATE
        )
        yield [cert_1_desc]

    def create_transactions_tops87(self, measure_creator, measure_ender, new_measures, transaction, counters):
        params = {
            'regulation_group': Group.objects.get(group_id='FTA'),
            'published_at': datetime(2021, 3, 3),
            'approved': True,
            'valid_between': DateTimeTZRange(
                datetime(2021, 3, 5), None
            ),
            'information_text': 'The Customs Tariff (Preferential Trade Arrangements) (EU Exit) (Amendment) Regulations 2021',
            'public_identifier': 'S.I. 2021/241',
            'url': 'https://www.legislation.gov.uk/uksi/2021/241'
        }
        generating_regulation = Regulation.objects.create(
            regulation_id='P2102410',
            role_type=RoleType.BASE,
            transaction=transaction,
            update_type=UpdateType.CREATE,
            **params,
        )
        yield [generating_regulation]
        yield from self.process_measure_sheet(
            measure_creator,
            measure_ender,
            new_measures,
            update=True,
        )

    def create_transactions_tops11(self, measure_creator, measure_ender, data, transaction, counters):
        footnotes = data['tops-11a']
        new_description_rows = data['tops-11b']
        new_descriptions = {}
        for row in new_description_rows:
            new_descriptions[str(row[0].value)] = str(row[1].value)
        for row in footnotes:
            footnote_description_period_sid = str(row[0].value)
            footnote_type_id = str(row[1].value)
            footnote_id = str(row[2].value)
            validity_start_date = parse_date(row[3])
            old_description = str(row[4].value)

            new_description = new_descriptions[footnote_type_id + footnote_id]
            if old_description == new_description:
                raise ValueError('Old and new description are same.')
            if validity_start_date > datetime(2021, 1, 1):
                continue#raise ValueError(f'Footnote description dates not expected to be after Brexit: {validity_start_date}.')
            elif validity_start_date == datetime(2021, 1, 1):
                new_footnote_description = FootnoteDescription.objects.create(
                    description_period_sid=counters["footnote_description_sid_counter"](),
                    described_footnote=Footnote.objects.current().get(
                        footnote_type=FootnoteType.objects.get(
                            footnote_type_id=footnote_type_id,
                        ),
                        footnote_id=footnote_id
                    ),
                    description=new_description,
                    valid_between=BREXIT_TO_INFINITY,
                    transaction=transaction,
                    update_type=UpdateType.CREATE,
                )
                yield [new_footnote_description]

            else:
                new_footnote_description = FootnoteDescription.objects.current().get(
                    description_period_sid=footnote_description_period_sid,
                )
                new_footnote_description.transaction = transaction
                new_footnote_description.update_type = UpdateType.UPDATE
                new_footnote_description.description = new_description
                yield [new_footnote_description]

    def create_transactions_tops13(self, measure_creator, measure_ender, data, transaction, counters):
        certificates = data['tops-13a']
        new_description_rows = data['tops-13b']
        new_descriptions = {}
        for row in new_description_rows:
            new_descriptions[str(row[0].value)] = str(row[1].value)
        for row in certificates:
            certificate_description_period_sid = str(row[0].value)
            certificate_type_code = str(row[1].value)
            certificate_code = str(row[2].value)
            validity_start_date = parse_date(row[3])
            old_description = str(row[4].value)

            new_description = new_descriptions[certificate_type_code + certificate_code]
            if old_description == new_description:
                raise ValueError('Old and new description are same.')
            if validity_start_date > datetime(2021, 1, 1):
                continue #raise ValueError(f'Footnote description dates not expected to be after Brexit: {validity_start_date}.')
            elif validity_start_date == datetime(2021, 1, 1):
                new_certificate_description = CertificateDescription.objects.create(
                    sid=counters["certificate_description_sid_counter"](),
                    described_certificate=Certificate.objects.current().get(
                        certificate_type=CertificateType.objects.get(
                            sid=certificate_type_code,
                        ),
                        sid=certificate_code
                    ),
                    description=new_description,
                    valid_between=BREXIT_TO_INFINITY,
                    transaction=transaction,
                    update_type=UpdateType.CREATE,
                )
                yield [new_certificate_description]

            else:
                logger.debug(certificate_description_period_sid)
                new_certificate_description = CertificateDescription.objects.current().get(
                    sid=certificate_description_period_sid,
                )
                new_certificate_description.transaction = transaction
                new_certificate_description.update_type = UpdateType.UPDATE
                new_certificate_description.description = new_description
                yield [new_certificate_description]

    def create_transactions_tops91(self, measure_creator, measure_ender, measures, transaction, counters):
        measures1, measures2 = tee(measures)
        yield from self.process_measure_sheet(
            measure_creator,
            measure_ender,
            measures1,
        )
        processed = set()
        for row in measures2:
            origins = QuotaOrderNumberOrigin.objects.current().filter(
                order_number=QuotaOrderNumber.objects.current().get(
                    order_number=blank(row[15].value, str)
                )
            ).all()
            for origin in origins:
                if origin.sid in processed:
                    continue
                origin.transaction = transaction
                origin.update_type = UpdateType.DELETE
                yield [origin]
                processed.add(origin.sid)

    def create_transactions_tops63(self, measure_creator, measure_ender, measures, transaction, counters):
        yield from self.process_measure_sheet(
            measure_creator,
            measure_ender,
            measures,
        )

    def create_transactions_tops90(self, measure_creator, measure_ender, measures, transaction, counters):
        new_certificate_description = CertificateDescription.objects.create(
            sid=counters["certificate_description_sid_counter"](),
            described_certificate=Certificate.objects.current().get(
                certificate_type=CertificateType.objects.get(
                    sid='C',
                ),
                sid='001'
            ),
            description='Attestation of Equivalence for the importation of hops and hop products into Great Britain',
            valid_between=DateTimeTZRange(
                datetime(2021, 7, 1)
            ),
            transaction=transaction,
            update_type=UpdateType.CREATE,
        )
        yield [new_certificate_description]

        yield from self.process_measure_sheet(
            measure_creator,
            measure_ender,
            measures,
        )

    def create_transactions_tops92(self, measure_creator, measure_ender, measures, transaction, counters):
        yield from self.process_measure_sheet(
            measure_creator,
            measure_ender,
            measures,
        )

    def create_transactions_tops98(self, measure_creator, measure_ender, data, transaction_model, counters):
        cc_operations = data['tops-98a']
        new_measures = data['tops-98b']
        yield from update_commodity_codes.Command().create_transactions(
            measure_creator, measure_ender, cc_operations, [], transaction_model, auto_migrate=False
        )

        yield from self.process_measure_sheet(
            measure_creator,
            measure_ender,
            new_measures,
        )

    def create_transactions_tops99(self, measure_creator, measure_ender, data, transaction_model, counters):
        yield from self.process_measure_sheet(
            measure_creator,
            measure_ender,
            data,
        )

    def create_transactions_tops108(self, measure_creator, measure_ender, data, transaction_model, counters):
        yield from self.process_measure_sheet(
            measure_creator,
            measure_ender,
            data,
            update=True,
        )

    def create_transactions_tops109(self, measure_creator, measure_ender, data, transaction_model, counters):
        sids = ['200432', '200434', '200534']
        for sid in sids:
            new_footnote_description = FootnoteDescription.objects.current().get(
                description_period_sid=sid,
            )
            new_footnote_description.transaction = transaction_model
            new_footnote_description.update_type = UpdateType.UPDATE
            new_footnote_description.description = new_footnote_description.description.replace("&commat;", "&#64;")
            yield [new_footnote_description]

    def create_transactions_tops104(self, measure_creator, measure_ender, data, transaction_model, counters):
        yield list(add_geo_area_members(
            valid_between=DateTimeTZRange(
                datetime(2021, 4, 14), None
            ),
            transaction=transaction_model,
            group_area=351,
            member_area_sids=[
                95,    # Suriname
            ],
        ))

    def create_transactions_tops110(self, measure_creator, measure_ender, data, transaction_model, counters):
        yield from self.process_measure_sheet(
            measure_creator,
            measure_ender,
            data,
        )

    def create_transactions_tops111(self, measure_creator, measure_ender, data, transaction, counters):
        new_footnote = Footnote.objects.create(
            footnote_type=FootnoteType.objects.current().get(
                footnote_type_id='CD'
            ),
            footnote_id='856',
            valid_between=BREXIT_TO_INFINITY,
            transaction=transaction,
            update_type=UpdateType.CREATE,
        )
        new_footnote_description = FootnoteDescription.objects.create(
            description_period_sid=counters["footnote_description_sid_counter"](),
            described_footnote=new_footnote,
            description='If the machinery has been used, an N851 Phytosanitary Certificate is required as it may contain soil.',
            valid_between=BREXIT_TO_INFINITY,
            transaction=transaction,
            update_type=UpdateType.CREATE,
        )
        yield [new_footnote, new_footnote_description]

        cert_1 = Certificate(
            sid='067',
            valid_between=BREXIT_TO_INFINITY,
            certificate_type=CertificateType.objects.current().get(
                sid='Y'
            ),
            transaction=transaction,
            update_type=UpdateType.CREATE
        )
        cert_1.save()
        cert_1_desc = CertificateDescription(
            sid=counters['certificate_description_sid_counter'](),
            description='Machinery is new.',
            described_certificate=cert_1,
            valid_between=BREXIT_TO_INFINITY,
            transaction=transaction,
            update_type=UpdateType.CREATE
        )
        yield [cert_1, cert_1_desc]

        yield from self.process_measure_sheet(
            measure_creator,
            measure_ender,
            data,
        )

    def create_transactions_tops115(self, measure_creator, measure_ender, data, transaction, counters):
        sids = ['200429', '200430', '200431', '200440', '200441']
        for sid in sids:
            new_footnote_description = FootnoteDescription.objects.current().get(
                description_period_sid=sid,
            )
            new_footnote_description.transaction = transaction
            new_footnote_description.update_type = UpdateType.UPDATE
            new_footnote_description.description = new_footnote_description.description\
                .replace("<sub>m</sub>", "&#64;m")\
                .replace("<sub>d</sub>", "&#64;d")\
                .replace("<sub>r</sub>", "&#64;r")\
                .replace("<sub>f</sub>", "&#64;f")
            yield [new_footnote_description]

    def create_transactions_tops114(self, measure_creator, measure_ender, data, transaction, counters):
        measure_type_ids = ['145', '115', '464', '105', '146', '123']
        for type in measure_type_ids:
            measure_type = MeasureType.objects.current().get(sid=type)
            measure_type.transaction = transaction
            measure_type.update_type = UpdateType.UPDATE
            measure_type.description = measure_type.description.replace("end-use", "authorised use")
            yield [measure_type]

    def create_transactions_tops61(self, measure_creator, measure_ender, data, transaction, counters):
        quota_order_number = QuotaOrderNumber(
            sid=counters['order_number_sid_counter'](),
            order_number='054324',
            update_type=UpdateType.CREATE,
            transaction=transaction,
            mechanism=AdministrationMechanism.FCFS,
            category=QuotaCategory.PREFERENTIAL,
            valid_between=BREXIT_TO_INFINITY,
        )
        quota_order_number.save()
        origin = QuotaOrderNumberOrigin(
            sid=counters['order_number_origin_sid_counter'](),
            order_number=quota_order_number,
            geographical_area=GeographicalArea.objects.current().get(
                sid=376
            ),
            update_type=UpdateType.CREATE,
            transaction=transaction,
            valid_between=quota_order_number.valid_between,
        )
        origin.save()
        definition = QuotaDefinition(
            sid=counters['quota_definition_sid_counter'](),
            order_number=quota_order_number,
            initial_volume=136000,
            volume=136000,
            valid_between=DateTimeTZRange(
                BREXIT,
                datetime(2021, 12, 31)
            ),
            maximum_precision=3,
            quota_critical_threshold=90,
            measurement_unit=MeasurementUnit.objects.get(code="KGM"),
            update_type=UpdateType.CREATE,
            transaction=transaction,
        )
        definition.save()
        yield [quota_order_number, origin, definition]

        yield from self.process_measure_sheet(
            measure_creator,
            measure_ender,
            data,
        )

    def create_transactions_tops83(self, measure_creator, measure_ender, data, transaction, counters):
        yield from self.process_measure_sheet(
            measure_creator,
            measure_ender,
            data,
        )

    def create_transactions_tops118(self, measure_creator, measure_ender, data, transaction, counters):
        yield from self.process_measure_sheet(
            measure_creator,
            measure_ender,
            data,
        )

    def create_transactions_tops84(self, measure_creator, measure_ender, new_measures, transaction, counters):
        # code 2600/2601 description updates
        old_description = AdditionalCodeDescription.objects.current().get(
            description_period_sid='11001'
        )
        description = old_description.new_draft(workbasket=transaction.workbasket, save=False)
        description.description = 'Goods that are COVID-19 critical are exempt from import duty - see footnote for coverage. Please do not use if the MFN import duty rate is 0%.'
        description.transaction = transaction
        description.update_type = UpdateType.UPDATE
        yield [description]

        old_description = AdditionalCodeDescription.objects.current().get(
            description_period_sid='11000'
        )
        description = old_description.new_draft(workbasket=transaction.workbasket, save=False)
        description.description = 'Duty suspension does not apply. Please do not use if the MFN import duty rate is 0%.'
        description.transaction = transaction
        description.update_type = UpdateType.UPDATE
        yield [description]

        # code 2500
        old_description = AdditionalCodeDescription.objects.current().get(
            description_period_sid='10028'
        )
        description = old_description.new_draft(workbasket=transaction.workbasket, save=False)
        description.description = 'INN 0% import duty applies - see footnote for coverage. Please do not use if the MFN import duty rate is 0%.'
        description.transaction = transaction
        description.update_type = UpdateType.UPDATE
        yield [description]

        # code 2501
        add_code = AdditionalCode.objects.current().get(
            sid='3767',
        )
        add_code_desc = AdditionalCodeDescription(
            description_period_sid=counters['additional_code_description_period_sid_counter'](),
            described_additional_code=add_code,
            description='Duty suspension does not apply. Please do not use if the MFN import duty rate is 0%.',
            valid_between=BREXIT_TO_INFINITY,
            transaction=transaction,
            update_type=UpdateType.CREATE
        )
        yield [add_code_desc]

        # code 2700
        add_code = AdditionalCode(
            sid=counters['additional_code_sid_counter'](),
            type=AdditionalCodeType.objects.current().get(
                sid='2',
            ),
            code='700',
            valid_between=BREXIT_TO_INFINITY,
            transaction=transaction,
            update_type=UpdateType.CREATE
        )
        add_code_desc = AdditionalCodeDescription(
            description_period_sid=counters['additional_code_description_period_sid_counter'](),
            described_additional_code=add_code,
            description='Duty suspension of 0% applies - see footnote for coverage. Please do not use if the MFN import duty rate is 0%.',
            valid_between=BREXIT_TO_INFINITY,
            transaction=transaction,
            update_type=UpdateType.CREATE
        )
        yield [add_code, add_code_desc]

        # code 2701
        add_code = AdditionalCode(
            sid=counters['additional_code_sid_counter'](),
            type=AdditionalCodeType.objects.current().get(
                sid='2',
            ),
            code='701',
            valid_between=BREXIT_TO_INFINITY,
            transaction=transaction,
            update_type=UpdateType.CREATE
        )
        add_code_desc = AdditionalCodeDescription(
            description_period_sid=counters['additional_code_description_period_sid_counter'](),
            described_additional_code=add_code,
            description='Duty suspension does not apply. Please do not use if the MFN import duty rate is 0%.',
            valid_between=BREXIT_TO_INFINITY,
            transaction=transaction,
            update_type=UpdateType.CREATE
        )
        yield [add_code, add_code_desc]

        # code 2702
        add_code = AdditionalCode(
            sid=counters['additional_code_sid_counter'](),
            type=AdditionalCodeType.objects.current().get(
                sid='2',
            ),
            code='702',
            valid_between=BREXIT_TO_INFINITY,
            transaction=transaction,
            update_type=UpdateType.CREATE
        )
        add_code_desc = AdditionalCodeDescription(
            description_period_sid=counters['additional_code_description_period_sid_counter'](),
            described_additional_code=add_code,
            description='Partial duty suspension of 2% applies - see footnote for coverage. Please do not use if the MFN import duty rate is 0%.',
            valid_between=BREXIT_TO_INFINITY,
            transaction=transaction,
            update_type=UpdateType.CREATE
        )
        yield [add_code, add_code_desc]

    def create_transactions_tops95(self, measure_creator, measure_ender, new_measures, transaction, counters):
        yield from self.process_measure_sheet(
            measure_creator,
            measure_ender,
            new_measures,
        )

    def create_transactions_tops128(self, measure_creator, measure_ender, new_measures, transaction, counters):
        yield from self.process_measure_sheet(
            measure_creator,
            measure_ender,
            new_measures,
        )

    def create_transactions_tops94(self, measure_creator, measure_ender, new_measures, transaction, counters):
        yield from self.process_measure_sheet(
            measure_creator,
            measure_ender,
            new_measures,
        )

    def create_transactions_tops125(self, measure_creator, measure_ender, data, transaction_model, counters):
        yield from update_commodity_codes.Command().create_transactions(
            measure_creator, measure_ender, data, [], transaction_model, auto_migrate=False
        )

    def create_transactions_tops130(self, measure_creator, measure_ender, new_measures, transaction_model, counters):
        yield from self.process_measure_sheet(
            measure_creator,
            measure_ender,
            new_measures,
        )

    def create_transactions_tops132(self, measure_creator, measure_ender, data, transaction_model,
                                   counters):
        cc_operations = data['tops-132a']
        cc_measures = data['tops-132b']
        new_measures = data['tops-132c']
        yield from update_commodity_codes.Command().create_transactions(
            measure_creator, measure_ender, cc_operations, cc_measures, transaction_model, auto_migrate=False
        )

        yield from self.process_measure_sheet(
            measure_creator,
            measure_ender,
            new_measures,
        )

    def create_transactions_tops67(self, measure_creator, measure_ender, new_measures, transaction, counters):
        cert_1_desc = CertificateDescription(
            sid=counters['certificate_description_sid_counter'](),
            description='Other certificates: Common Health Entry Document for Feed and Food of Non-Animal Origin (CHED-D) (as set out in Part 2, Section D of Annex II to Commission Implementing Regulation (EU) 2019/1715 (OJ L 261)) as transposed into UK Law.',
            described_certificate=Certificate.objects.current().get(
                sid='678',
                certificate_type=CertificateType.objects.current().get(
                    sid='C'
                ),

            ),
            valid_between=BREXIT_TO_INFINITY,
            transaction=transaction,
            update_type=UpdateType.CREATE
        )
        yield [cert_1_desc]

        cert_1_desc = CertificateDescription(
            sid=counters['certificate_description_sid_counter'](),
            description='UN/EDIFACT certificates: Common Health Entry Document for Products (CHED-P) (as set out in Part 2, Section B of Annex II to Commission Implementing Regulation (EU) 2019/1715 (OJ L 261)) as transposed into UK Law.',
            described_certificate=Certificate.objects.current().get(
                sid='853',
                certificate_type=CertificateType.objects.current().get(
                    sid='N'
                ),

            ),
            valid_between=BREXIT_TO_INFINITY,
            transaction=transaction,
            update_type=UpdateType.CREATE
        )
        yield [cert_1_desc]

        cert_1_desc = CertificateDescription(
            sid=counters['certificate_description_sid_counter'](),
            description='The declared goods are not concerned by Commission Implementing Regulation (EU) 2019/1787 as transposed into UK Law.',
            described_certificate=Certificate.objects.current().get(
                sid='928',
                certificate_type=CertificateType.objects.current().get(
                    sid='Y'
                ),

            ),
            valid_between=BREXIT_TO_INFINITY,
            transaction=transaction,
            update_type=UpdateType.CREATE
        )
        yield [cert_1_desc]

        cert_1_desc = CertificateDescription(
            sid=counters['certificate_description_sid_counter'](),
            description='Particular provisions: The declared goods are not concerned by Commission Decision 2007/275/EC and Commission Implementing Regulation (EU) 2019/2007 as transposed into UK Law.',
            described_certificate=Certificate.objects.current().get(
                sid='930',
                certificate_type=CertificateType.objects.current().get(
                    sid='Y'
                ),

            ),
            valid_between=BREXIT_TO_INFINITY,
            transaction=transaction,
            update_type=UpdateType.CREATE
        )
        yield [cert_1_desc]

        cert_1_desc = CertificateDescription(
            sid=counters['certificate_description_sid_counter'](),
            description='Particular provisions: Goods benefitting from derogation to veterinary controls according to Article 6.1b of Commission Decision (EC) No 275/2007 as transposed into UK Law.',
            described_certificate=Certificate.objects.current().get(
                sid='931',
                certificate_type=CertificateType.objects.current().get(
                    sid='Y'
                ),

            ),
            valid_between=BREXIT_TO_INFINITY,
            transaction=transaction,
            update_type=UpdateType.CREATE
        )
        yield [cert_1_desc]

        footnote = Footnote.objects.current().get(
            footnote_type=FootnoteType.objects.get(
                footnote_type_id='TN',
            ),
            footnote_id='084'
        )
        new_footnote_description = FootnoteDescription(
            description_period_sid=counters["footnote_description_sid_counter"](),
            described_footnote=footnote,
            description='Products consigned from Japan shall be accompanied by a Common Health Entry Document for Feed and Food of Non-Animal Origin (CHED-D) or a Common Health Entry Document for Products (CHED-P) according to Commission Implementing Regulation (EU) 2019/1787 as transposed into UK law. See <a href="https://www.legislation.gov.uk/eur/2019/1787/contents">[2019/1787]</a> for specific coverage.',
            valid_between=DateTimeTZRange(datetime(2021, 1, 1), None),
            transaction=transaction,
            update_type=UpdateType.CREATE,
        )
        yield [new_footnote_description]

        yield from self.process_measure_sheet(
            measure_creator,
            measure_ender,
            new_measures
        )

    def create_transactions_tops112(self, measure_creator, measure_ender, existing_measures, transaction, counters):
        cert_1_desc = CertificateDescription(
            sid=counters['certificate_description_sid_counter'](),
            description='Notification document for import/export of hazardous or mixed notifiable waste. See Article 4 and Annex IA of Regulation (EC) No 1013/2006 as retained in UK law (<a href="https://www.legislation.gov.uk/eur/2006/1013/contents">https://www.legislation.gov.uk/eur/2006/1013/contents</a>).',
            described_certificate=Certificate.objects.current().get(
                sid='669',
                certificate_type=CertificateType.objects.current().get(
                    sid='C'
                ),

            ),
            valid_between=BREXIT_TO_INFINITY,
            transaction=transaction,
            update_type=UpdateType.CREATE
        )
        yield [cert_1_desc]

        cert_1_desc = CertificateDescription(
            sid=counters['certificate_description_sid_counter'](),
            description='Movement document for import/export of hazardous or mixed notifiable waste. See Article 4 and Annex IB of Regulation (EC) No 1013/2006 as retained in UK law (<a href="https://www.legislation.gov.uk/eur/2006/1013/contents">https://www.legislation.gov.uk/eur/2006/1013/contents</a>).',
            described_certificate=Certificate.objects.current().get(
                sid='670',
                certificate_type=CertificateType.objects.current().get(
                    sid='C'
                ),

            ),
            valid_between=BREXIT_TO_INFINITY,
            transaction=transaction,
            update_type=UpdateType.CREATE
        )
        yield [cert_1_desc]

        cert_1_desc = CertificateDescription(
            sid=counters['certificate_description_sid_counter'](),
            description='Information document for export of non-hazardous waste or imports of non-hazardous waste from EU. See Article 18 and Annex VII of Regulation (EC) No 1013/2006 as retained in UK law (<a href="https://www.legislation.gov.uk/eur/2006/1013/contents">https://www.legislation.gov.uk/eur/2006/1013/contents</a>).',
            described_certificate=Certificate.objects.current().get(
                sid='672',
                certificate_type=CertificateType.objects.current().get(
                    sid='C'
                ),

            ),
            valid_between=BREXIT_TO_INFINITY,
            transaction=transaction,
            update_type=UpdateType.CREATE
        )
        yield [cert_1_desc]

        cert_1_desc = CertificateDescription(
            sid=counters['certificate_description_sid_counter'](),
            description='Products not considered as waste according to Regulation (EC) No 1013/2006 as retained in UK law (<a href="https://www.legislation.gov.uk/eur/2006/1013/contents">https://www.legislation.gov.uk/eur/2006/1013/contents</a>).',
            described_certificate=Certificate.objects.current().get(
                sid='923',
                certificate_type=CertificateType.objects.current().get(
                    sid='Y'
                ),

            ),
            valid_between=BREXIT_TO_INFINITY,
            transaction=transaction,
            update_type=UpdateType.CREATE
        )
        yield [cert_1_desc]

        new_footnote = Footnote.objects.create(
            footnote_type=FootnoteType.objects.current().get(
                footnote_type_id='PR'
            ),
            footnote_id='019',
            valid_between=BREXIT_TO_INFINITY,
            transaction=transaction,
            update_type=UpdateType.CREATE,
        )
        new_footnote_description = FootnoteDescription.objects.create(
            description_period_sid=counters["footnote_description_sid_counter"](),
            described_footnote=new_footnote,
            description='These certification requirements only apply to the import and export of "waste" as defined in EC Regulation 1013/2006 as retained UK law (<a href="https://www.legislation.gov.uk/eur/2006/1013/contents">https://www.legislation.gov.uk/eur/2006/1013/contents</a>). For further advice please go to <a href="https://www.gov.uk/government/publications/waste-exports-control-tool">https://www.gov.uk/government/publications/waste-exports-control-tool</a>.',
            valid_between=BREXIT_TO_INFINITY,
            transaction=transaction,
            update_type=UpdateType.CREATE,
        )

        yield [new_footnote, new_footnote_description]

        for row in (OldMeasureRow(row) for row in existing_measures):
            measure = Measure.objects.current().get(
                sid=row.measure_sid
            )
            # create new footnote association
            new_fn = Footnote.objects.current().get(
                footnote_id='019', footnote_type__footnote_type_id='PR'
            )
            association = FootnoteAssociationMeasure(
                footnoted_measure=measure,
                associated_footnote=new_fn,
                update_type=UpdateType.CREATE,
                transaction=transaction,
            )
            yield [association]

    def create_transactions_tops119(self, measure_creator, measure_ender, existing_measures, transaction, counters):
        # replace footnotes with new footnotes
        for row in (OldMeasureRow(row) for row in existing_measures):
            measure = Measure.objects.current().get(
                sid=row.measure_sid
            )
            # remove old footnote associations
            old_fn_associations = []
            for old_fn in measure.footnotes.all():
                old_fn_association = FootnoteAssociationMeasure.objects.current().get(
                    footnoted_measure=measure,
                    associated_footnote=old_fn
                )
                old_fn_association.update_type = UpdateType.DELETE
                old_fn_association.transaction = transaction
                old_fn_associations.append(old_fn_association)

            # create new footnote association
            new_fn = Footnote.objects.current().get(
                footnote_id=row.footnotes[0][2:], footnote_type__footnote_type_id=row.footnotes[0][0:2]
            )
            new_fn_association = FootnoteAssociationMeasure(
                footnoted_measure=measure,
                associated_footnote=new_fn,
                update_type=UpdateType.CREATE,
                transaction=transaction,
            )
            yield old_fn_associations + [new_fn_association]

        # clean up unused footnotes
        footnotes = [('PR', '007'), ('PR', '015'), ('PR', '016')]
        for footnote_type_id, footnote_id in footnotes:
            footnote = Footnote.objects.current().get(
                footnote_type=FootnoteType.objects.get(
                    footnote_type_id=footnote_type_id,
                ),
                footnote_id=footnote_id,
            )
            footnote.update_type = UpdateType.DELETE
            footnote.transaction = transaction

            footnote_description = FootnoteDescription.objects.current().get(
                described_footnote=footnote
            )
            footnote_description.update_type = UpdateType.DELETE
            footnote_description.transaction = transaction

            yield [footnote, footnote_description]


    def create_transactions_tops113(self, measure_creator, measure_ender, existing_measures, transaction_model, counters):
            new_footnote_description = FootnoteDescription.objects.current().get(
                description_period_sid=200431,
            )
            new_footnote_description.transaction = transaction_model
            new_footnote_description.update_type = UpdateType.UPDATE
            new_footnote_description.description = 'For further advice or to get a Phytosanitary certificate, contact: <P>HMI Admin Support,</P><P>(CIT), APHA, Defra, Foss House,</P><P>Kings Pool 1-2 Peasholme Green,</P><P>York, YO1 7PX</P><P>Tel: 0300 100 0313</P><P>Email: peachenquiries&#64;apha.gov.uk</P>'
            yield [new_footnote_description]

            yield from self.process_measure_sheet(
                measure_creator,
                measure_ender,
                existing_measures
            )

    def create_transactions_tops124(self, measure_creator, measure_ender, new_measures, transaction, counters):
            yield from self.process_measure_sheet(
                measure_creator,
                measure_ender,
                new_measures
            )

    def create_transactions_tops151(self, measure_creator, measure_ender, measures, transaction, counters):
        measures1, measures2 = tee(measures)
        processed = set()
        for row in measures2:
            origins = QuotaOrderNumberOrigin.objects.filter(
                order_number=QuotaOrderNumber.objects.current().get(
                    order_number=blank(row[15].value, str)
                ),
                geographical_area=GeographicalArea.objects.current().get(
                    sid=blank(row[13].value, str)
                )
            ).all()
            for origin in origins:
                if origin.sid in processed:
                    continue
                processed.add(origin.sid)
                origin.sid = counters['order_number_origin_sid_counter']()
                origin.transaction = transaction
                origin.update_type = UpdateType.CREATE
                yield [origin]

        yield from self.process_measure_sheet(
            measure_creator,
            measure_ender,
            measures1,
        )

    def create_transactions_tops141(self, measure_creator, measure_ender, measures, transaction, counters):
        new_certificate_description = CertificateDescription.objects.current().get(
            sid=5000,
        )
        new_certificate_description.transaction = transaction
        new_certificate_description.update_type = UpdateType.UPDATE
        new_certificate_description.description = 'Goods for which an export licence is not required. Please use the <a href="https://www.ecochecker.trade.gov.uk/spirefox5live/fox/spire/OGEL_GOODS_CHECKER_LANDING_PAGE/new">Goods Checker</a> to determine whether your items are controlled and whether you need an export licence from the <a href="https://www.gov.uk/government/organisations/export-control-organisation">Export Control Joint Unit</a>.'
        yield [new_certificate_description]

    def create_transactions_tops120(self, measure_creator, measure_ender, measures, transaction, counters):

        quotas = [
            ('051526', '4638.263', datetime(2021, 12, 31), 'HLT'),
            ('051527', '1037', datetime(2021, 12, 31), 'HLT'),
            ('051534', '421', datetime(2021, 12, 31), 'HLT'),
            ('051545', '1238', datetime(2021, 12, 31), 'KGM'),
            ('051546', '7430', datetime(2021, 12, 31), 'KGM'),
            ('051592', '1238', datetime(2021, 12, 31), 'KGM'),
            ('054198', '734', datetime(2021, 12, 31), 'TNE'),
            ('054326', '9050', datetime(2021, 9, 30), 'TNE'),
        ]
        for order_number, volume, quota_end, measurment_unit in quotas:
            if order_number == '051534':
                quota_order_number = QuotaOrderNumber.objects.current().get(
                    order_number='051534',
                )
                existing_origin = QuotaOrderNumberOrigin.objects.current().get(
                    order_number=quota_order_number,
                )
                existing_origin.transaction = transaction
                existing_origin.update_type = UpdateType.DELETE
                yield [existing_origin]

                exisiting_definition = QuotaDefinition.objects.current().get(
                    order_number=quota_order_number,
                )
                exisiting_definition.transaction = transaction
                exisiting_definition.update_type = UpdateType.DELETE
                yield [exisiting_definition]
            else:
                quota_order_number = QuotaOrderNumber(
                    sid=counters['order_number_sid_counter'](),
                    order_number=order_number,
                    update_type=UpdateType.CREATE,
                    transaction=transaction,
                    valid_between=BREXIT_TO_INFINITY,
                    mechanism=AdministrationMechanism.FCFS,
                    category=QuotaCategory.PREFERENTIAL,
                )
                quota_order_number.save()

            origin = QuotaOrderNumberOrigin(
                sid=counters['order_number_origin_sid_counter'](),
                order_number=quota_order_number,
                geographical_area=GeographicalArea.objects.current().get(
                    sid=346
                ),
                update_type=UpdateType.CREATE,
                transaction=transaction,
                valid_between=quota_order_number.valid_between,
            )
            origin.save()
            definition = QuotaDefinition(
                sid=counters['quota_definition_sid_counter'](),
                order_number=quota_order_number,
                initial_volume=volume,
                volume=volume,
                valid_between=DateTimeTZRange(
                    datetime(2021, 5, 20),
                    quota_end
                ),
                maximum_precision=3,
                quota_critical_threshold=90,
                measurement_unit=MeasurementUnit.objects.get(code=measurment_unit),
                update_type=UpdateType.CREATE,
                transaction=transaction,
            )
            definition.save()
            # leave out origin for 051534 until post exhaustion
            yield [definition] if order_number == '051534' else [quota_order_number, origin, definition]

        yield from self.process_measure_sheet(
            measure_creator,
            measure_ender,
            measures,
        )

    def create_transactions_tops50(self, measure_creator, measure_ender, new_measures, transaction, counters):
        # code 2700
        add_code = AdditionalCode(
            sid=counters['additional_code_sid_counter'](),
            type=AdditionalCodeType.objects.current().get(
                sid='2',
            ),
            code='700',
            valid_between=BREXIT_TO_INFINITY,
            transaction=transaction,
            update_type=UpdateType.CREATE
        )
        add_code.save(force_write=True)
        add_code_desc = AdditionalCodeDescription(
            description_period_sid=counters['additional_code_description_period_sid_counter'](),
            described_additional_code=add_code,
            description='Duty suspension of 0% applies - see footnote for coverage. Please do not use if the MFN import duty rate is 0%.',
            valid_between=BREXIT_TO_INFINITY,
            transaction=transaction,
            update_type=UpdateType.CREATE
        )
        yield [add_code, add_code_desc]

        # code 2701
        add_code = AdditionalCode(
            sid=counters['additional_code_sid_counter'](),
            type=AdditionalCodeType.objects.current().get(
                sid='2',
            ),
            code='701',
            valid_between=BREXIT_TO_INFINITY,
            transaction=transaction,
            update_type=UpdateType.CREATE
        )
        add_code.save(force_write=True)
        add_code_desc = AdditionalCodeDescription(
            description_period_sid=counters['additional_code_description_period_sid_counter'](),
            described_additional_code=add_code,
            description='Duty suspension does not apply. Please do not use if the MFN import duty rate is 0%.',
            valid_between=BREXIT_TO_INFINITY,
            transaction=transaction,
            update_type=UpdateType.CREATE
        )
        yield [add_code, add_code_desc]

        # code 2702
        add_code = AdditionalCode(
            sid=counters['additional_code_sid_counter'](),
            type=AdditionalCodeType.objects.current().get(
                sid='2',
            ),
            code='702',
            valid_between=BREXIT_TO_INFINITY,
            transaction=transaction,
            update_type=UpdateType.CREATE
        )
        add_code.save(force_write=True)
        add_code_desc = AdditionalCodeDescription(
            description_period_sid=counters['additional_code_description_period_sid_counter'](),
            described_additional_code=add_code,
            description='Partial duty suspension of 2% applies - see footnote for coverage. Please do not use if the MFN import duty rate is 0%.',
            valid_between=BREXIT_TO_INFINITY,
            transaction=transaction,
            update_type=UpdateType.CREATE
        )
        yield [add_code, add_code_desc]

        descriptions = {
            "061": "This duty suspension only applies to Flurtamone (ISO) (CAS RN 96525-23-4) falling within this commodity code.",
            "062": "This duty suspension only applies to Chlorpyrifos (ISO) (CAS RN 2921-88-2) falling within this commodity code.",
            "063": "This duty suspension only applies to Microporous monolayer film of polypropylene or a microporous trilayer film of polypropylene, polyethylene and polypropylene, each film with<br>- zero transversal production direction (TD) shrinkage,<br>- a total thickness of 10 µm or more but not more than 50 µm,<br>- a width of 15 mm or more but not more than 900 mm,<br>- a length of more than 200 m but not more than 3000 m, and<br>- an average pore size between 0,02 µm and 0,1 µm<br> falling within this commodity code.",
            "064": "This duty suspension only applies to Gasket made of vulcanised rubber (ethylene-propylene-diene monomers), with permissible outflow of the material in the place of mold split of not more than 0,25 mm, in the shape of a rectangle:<br>- with a length of 72 mm or more but not more than 825 mm;<br>- with a width of 18 mm or more but not more than 155 mm<br> falling within this commodity code.",
            "065": "This duty suspension only applies to Non-wovens, consisting of poly(ethylene terephthlate) spun bonded media:<br>- of weight of 160 g/m<sup>2</sup> or more but not more than 300 g/m<sup>2</sup>,<br>- whether or not laminated on one side with a membrane or a membrane and aluminium<br>of a kind used for the manufacture of industrial filters falling within this commodity code.",
            "066": "This duty suspension only applies to Ceramic-carbon absorption cartridges with the following characteristics:<br>— extruded fired ceramic bound multicellular cylindrical structure,<br>- 10 % or more by weight but not more than 35 % y weight of activated carbon,<br>- 65 % or more by weight but not more than 90 % by weight of ceramic binder,<br>- with a diameter of 29 mm or more but not more than 41 mm,<br>- a length of not more than 150 mm,<br>- fired at temperature of 800 °C or more, and<br>- for vapours adsorption,<br>of a kind used for assembly in fuel vapours absorbers in fuel systems of motor vehicles falling within this commodity code.",
            "067": "This duty suspension only applies to Aluminium alloy rods with a diameter of 200 mm or more, but not exceeding 300 mm falling within this commodity code.",
            "068": "This duty suspension only applies to Titanium-aluminium-vanadium alloy (TiAl6V4) wire, of a diameter less than 20 mm and complying with AMS standards 4928, 4965 or 4967 falling within this commodity code.",
            "069": "This duty suspension only applies to Turbocharger cooling duct containing:<br>-an aluminum alloy duct with at least one metal holder and at least two mounting holes,<br>-a rubber pipe with clips,<br>-a stainless steel flange highly resistant to corrosion [SUS430JIL],<br>for use in the manufacture of compression ignition engines of motor vehicles falling within this commodity code.",
            "070": "This duty suspension only applies to Air membrane compressor with:<br>- a flow of 4,5 l/min or more, but not more than 7 l/min,<br>- power input of not more than 8,1 W, and<br>- a gauge pressure capacity not exceeding 400 hPa (0,4 bar)<br>of a kind used in the production of motor vehicle seats falling within this commodity code.",
            "072": "This duty suspension only applies to Car transfer case with single input, dual output, to distribute torque between front and rear axles in an aluminium housing, with dimension of not more than 565 × 570 × 510 mm, comprising:<br>- at least an actuator,<br>- whether or not an interior distribution by chain<br>falling within this commodity code.",
            "073": "This duty suspension only applies to Aluminium arc-welded removable receiver dryer with polyamide and ceramic elements with:<br>-a length of 143 mm or more but not more than 292 mm,<br>-a diameter of 31 mm or more but not more than 99 mm,<br>-a spangle length of not more than 0.2 mm and a thickness of not more than 0.06 mm, and <br>-a solid particle diameter of not more than 0.06 mm<br>of a kind used in car air-conditioning systems.",
            "074": "This duty suspension only applies to:<br>Unexpansible microspheres of a copolymer of acrylonitrile, methacrylonitrile and isobornyl methacrylate, of a diameter of 3 µm or more but not more than 4.6 µm<br>And<br>Electroplated interior or exterior decorative parts consisting of:<br>-a copolymer of acrylonitrile-butadiene-styrene (ABS), whether or not mixed with polycarbonate,<br>-layers of copper, nickel and chromium<br>for use in the manufacturing of parts for motor vehicles of heading 8701 to 8705<br>falling within this commodity code.",
        }
        footnote_ids = [
            '061',
            '062',
            '063',
            '064',
            '065',
            '066',
            '067',
            '068',
            '069',
            '070',
            '072',
            '073',
            '074',
        ]
        for fn_id in footnote_ids:
            new_footnote = Footnote.objects.create(
                footnote_type=FootnoteType.objects.current().get(
                    footnote_type_id='DS'
                ),
                footnote_id=fn_id,
                valid_between=BREXIT_TO_INFINITY,
                transaction=transaction,
                update_type=UpdateType.CREATE,
            )
            new_footnote.save(force_write=True)
            new_footnote_description = FootnoteDescription.objects.create(
                description_period_sid=counters["footnote_description_sid_counter"](),
                described_footnote=new_footnote,
                description=descriptions[fn_id],
                valid_between=BREXIT_TO_INFINITY,
                transaction=transaction,
                update_type=UpdateType.CREATE,
            )
            new_footnote_description.save(force_write=True)
            yield [new_footnote, new_footnote_description]

        descriptions = {
            "055": "This duty suspension only applies to Semiconductor module switch in a casing:<br>- consisting of an IGBT transistor chip and a diode chip on one or more lead frames,<br>- for a voltage of 600 V or 1 200 V<br>falling within this commodity code.",

        }
        update_footnote_ids = [
            '055',
        ]
        for footnote_id in update_footnote_ids:
            footnote = Footnote.objects.current().get(
                footnote_type=FootnoteType.objects.get(
                    footnote_type_id='DS',
                ),
                footnote_id=footnote_id,
            )
            footnote_description = FootnoteDescription.objects.current().get(
                described_footnote=footnote
            )
            footnote_description.update_type = UpdateType.UPDATE
            footnote_description.transaction = transaction
            footnote_description.description = descriptions[footnote_id]

            yield [footnote_description]


        # allow additional code type to be used for measure type 112
        add_code_measure_type_mapping = AdditionalCodeTypeMeasureType(
            measure_type=MeasureType.objects.get(
                 sid='112',
            ),
            additional_code_type=AdditionalCodeType.objects.get(
                 sid='2',
            ),
            valid_between=BREXIT_TO_INFINITY,
            transaction=transaction,
            update_type=UpdateType.CREATE,
        )
        yield [add_code_measure_type_mapping]

        # measure_type.measure_component_applicability_code = ApplicabilityCode.PERMITTED
        # measure_type.transaction = transaction
        # measure_type.update_type = UpdateType.UPDATE
        # yield [measure_type]

        yield from self.process_measure_sheet(
            measure_creator,
            measure_ender,
            new_measures,
        )

    def create_transactions_tops102(self, measure_creator, measure_ender, new_measures, transaction, counters):
        descriptions = {
            "075": "This duty suspension only applies to Preparation containing by weight:<br>-25% or more but not more than 50% of diethyl carbonate (CAS RN 105-58-8),<br>-25% or more but not more than 50% of ethylene carbonate (CAS RN 96-49-1),<br>-10% or more but not more than 20% of lithium hexafluorophosphate (CAS RN 21324-40-3),<br>-5% or more but not more than 10 % of ethyl methyl carbonate (CAS RN 623-53-0),<br>-1% or more but not more than 2% of vinylene carbonate (CAS RN 872-36-6),<br>-1% or more but not more than 2% of 4-fluoro-1,3-dioxolane-2-one (CAS RN 114435-02-8)<br>-not more than 1% of 1,5,2,4-Dioxadithiane 2,2,4,4-tetraoxide (CAS RN 99591-74-9) falling within this 10 digit commodity code. This suspension does not apply to any mixtures, preparations or products made up of different components containing these products."
        }
        new_footnote_ids = [
            '075',
        ]
        for fn_id in new_footnote_ids:
            new_footnote = Footnote.objects.create(
                footnote_type=FootnoteType.objects.current().get(
                    footnote_type_id='DS'
                ),
                footnote_id=fn_id,
                valid_between=BREXIT_TO_INFINITY,
                transaction=transaction,
                update_type=UpdateType.CREATE,
            )
            new_footnote.save(force_write=True)
            new_footnote_description = FootnoteDescription.objects.create(
                description_period_sid=counters["footnote_description_sid_counter"](),
                described_footnote=new_footnote,
                description=descriptions[fn_id],
                valid_between=BREXIT_TO_INFINITY,
                transaction=transaction,
                update_type=UpdateType.CREATE,
            )
            new_footnote_description.save(force_write=True)
            yield [new_footnote, new_footnote_description]

        descriptions = {
            "038": "This suspension only applies to Aqueous solution containing by weight:<br>- 10% or more but not more than 42% of 2-(3-chloro-5-(trifluoromethyl)pyridin-2-yl)ethanamine (CAS RN 658066-44-5),<br>- 10% or more but not more than 25% of sulphuric acid (CAS RN 7664-93-9), and<br>- 0.5% or more but not more than 2,9% of methanol (CAS RN 67-56-1)<br>and<br>- Diethylmethoxyborane (CAS RN 7397-46-8) in the form of a solution in tetrahydrofuran<br>and<br>-N2-[1-(S)-Ethoxycarbonyl-3-phenylpropyl]-N6-trifluoroacetyl-L-lysyl-N2-carboxy anhydride in a solution of dichloromethane at 37%<br> falling within this 10 digit commodity code. This suspension does not apply to any mixtures, preparations or products made up of different components containing these products.",
            "010": "This suspension only applies to:<br>- Diethyl carbonate (CAS RN 105-58-8), and<br>- Vinylene carbonate (CAS RN 872-36-6)<br>falling within this 10 digit commodity code. This suspension does not apply to any mixtures, preparations or products made up of different components containing these products.",
        }
        update_footnote_ids = [
            '038',
            '010'
        ]
        for footnote_id in update_footnote_ids:
            footnote = Footnote.objects.current().get(
                footnote_type=FootnoteType.objects.get(
                    footnote_type_id='DS',
                ),
                footnote_id=footnote_id,
            )
            footnote_description = FootnoteDescription.objects.current().get(
                described_footnote=footnote
            )
            footnote_description.update_type = UpdateType.UPDATE
            footnote_description.transaction = transaction
            footnote_description.description = descriptions[footnote_id]

            yield [footnote_description]

        yield from self.process_measure_sheet(
            measure_creator,
            measure_ender,
            new_measures,
        )

    def create_transactions_tops103old(self, measure_creator, measure_ender, data, transaction, counters):
        measures = data['tops-103a']
        footnotes = data['tops-103b']
        mfn_rates = data['tops-103d']
        old_measures, measures_copy = tee(measures)
        old_measures2, old_measures3 = tee(measures_copy)

        # additional codes
        add_code_mappings = [
            ('0.00%', '700'),
            ('0.00 GBP / 100 kg', '700'),
            ('2.00%', '702'),
            ('4.00%', '703'),
            ('6.00%', '704'),
            ('6.00% + 3.50 GBP / 100 kg', '705'),
            ('8.00%', '706'),
            ('10.00%', '707'),
            ('0.00% + 3.10 GBP / 100 kg / net drained wt', '708'),
        ]
        add_code_type_2 = AdditionalCodeType.objects.current().get(
            sid='2',
        )
        add_code_mappings_dict = dict(add_code_mappings)
        for duty, code in add_code_mappings[3:]:
            add_code = AdditionalCode(
                sid=counters['additional_code_sid_counter'](),
                type=add_code_type_2,
                code=code,
                valid_between=BREXIT_TO_INFINITY,
                transaction=transaction,
                update_type=UpdateType.CREATE
            )
            add_code.save(force_write=True)
            add_code_desc = AdditionalCodeDescription(
                description_period_sid=counters['additional_code_description_period_sid_counter'](),
                described_additional_code=add_code,
                description=f'Partial duty suspension of {duty} applies - see footnote for coverage. Please do not use if the MFN import duty rate is 0%.',
                valid_between=BREXIT_TO_INFINITY,
                transaction=transaction,
                update_type=UpdateType.CREATE
            )
            # yield [add_code, add_code_desc]

        # delete old measures
        yield from self.process_measure_sheet(
            measure_creator,
            measure_ender,
            old_measures,
        )

        # allow additional code 2 to be applied on measure type 115
        add_code_measure_type_mapping = AdditionalCodeTypeMeasureType(
            measure_type=MeasureType.objects.current().get(
                 sid='115',
            ),
            additional_code_type=AdditionalCodeType.objects.get(
                 sid='2',
            ),
            valid_between=BREXIT_TO_INFINITY,
            transaction=transaction,
            update_type=UpdateType.CREATE,
        )
        yield [add_code_measure_type_mapping]

        # create footnotes and mapping
        ds_fn_type = FootnoteType.objects.current().get(
            footnote_type_id='DS'
        )
        dx_fn_type = FootnoteType(
            footnote_type_id='DT',
            application_code=ds_fn_type.application_code,
            description=ds_fn_type.description,
            valid_between=ds_fn_type.valid_between,
            transaction=transaction,
            update_type=UpdateType.CREATE,
        )
        dx_fn_type.save(force_write=True)
        yield [dx_fn_type]

        dy_fn_type = FootnoteType(
            footnote_type_id='DV',
            application_code=ds_fn_type.application_code,
            description=ds_fn_type.description,
            valid_between=ds_fn_type.valid_between,
            transaction=transaction,
            update_type=UpdateType.CREATE,
        )
        dy_fn_type.save(force_write=True)
        yield [dy_fn_type]

        footnote_mapping = {}
        fn_id = 76
        fn_prefix = 'DS'
        existing_footnotes = {
            '2903740000': '002',
            '2905490000': '003',
            '2909500090': '004',
            '2914500090': '005',
            '2914790090': '006',
            '2915907090': '007',
            '2916399090': '008',
            '2920290090': '009',
            '2920901090': '010',
            '2921420090': '011',
            '2921430090': '012',
            '2921490090': '013',
            '2921511990': '014',
            '2921599090': '015',
            '2922290090': '016',
            '2922390090': '017',
            '2924190090': '018',
            '2924297099': '019',
            '2926907090': '020',
            '2930909899': '021',
            '2931399090': '022',
            '2931900090': '023',
            '2932190090': '024',
            '2932990090': '025',
            '2933199090': '026',
            '2933499090': '027',
            '2934999090': '028',
            '2935909099': '029',
            '3204170090': '030',
            '3204190090': '031',
            '3208101000': '032',
            '3215110000': '033',
            '3215190090': '034',
            '3402901090': '035',
            '3808939090': '036',
            '3808999090': '037',
            '3824999299': '038',
            '3901908099': '039',
            '3903909060': '040',
            '3906909090': '041',
            '3907100090': '042',
            '3907998090': '043',
            '3908900090': '044',
            '3919908099': '045',
            '3921905590': '046',
            '3926300090': '047',
            '8108200090': '048',
            '8108906090': '049',
            '8414592590': '050',
            '8507600090': '051',
            '8507903090': '052',
            '8507908099': '053',
            '8528590090': '054',
            '8535900089': '055',
            '8535900090': '055',
            '8537109899': '056',
            '8543709099': '057',
            '8708802090': '058',
            '8708809110': '059',
            '8708809120': '059',
            '8708809190': '059',
            '9401908090': '060',
        }
        # already updated in previous tickets
        updated_descriptions = ['DS010', 'DS038', 'DS055']
        for row in footnotes:
            code = str(row[0].value)
            # already done in previous ticket
            if code in (
                '3824999299',
                '2920901090',
                '2932190090',
                '2933399990',
                '3921190099',
                '3926909790',
                '4016930090',
                '5603149090',
                '6909190090',
                '7604291090',
                '8108903090',
                '8409990090',
                '8414808090',
                '8415900099',
                '8535900089',
                '8708809100',
            ):
                continue

            description = str(row[2].value)
            if code in existing_footnotes.keys():
                if existing_footnotes[code] not in updated_descriptions:
                    footnote = Footnote.objects.current().get(
                        footnote_type=FootnoteType.objects.get(
                            footnote_type_id='DS',
                        ),
                        footnote_id=existing_footnotes[code],
                    )
                    footnote_description = FootnoteDescription.objects.current().get(
                        described_footnote=footnote
                    )
                    footnote_description.update_type = UpdateType.UPDATE
                    footnote_description.transaction = transaction
                    footnote_description.description = description
                    yield [footnote_description]
                    updated_descriptions.append(existing_footnotes[code])
                else:
                    logger.debug(f'Description for DS{footnote.footnote_id} already updated')
                footnote_mapping[code] = f'DS{footnote.footnote_id}'

            else:
                new_footnote = Footnote.objects.create(
                    footnote_type=FootnoteType.objects.current().get(
                        footnote_type_id=fn_prefix
                    ),
                    footnote_id="{0:0=3d}".format(fn_id),
                    valid_between=BREXIT_TO_INFINITY,
                    transaction=transaction,
                    update_type=UpdateType.CREATE,
                )
                new_footnote.save(force_write=True)
                new_footnote_description = FootnoteDescription.objects.create(
                    description_period_sid=counters["footnote_description_sid_counter"](),
                    described_footnote=new_footnote,
                    description=description,
                    valid_between=BREXIT_TO_INFINITY,
                    transaction=transaction,
                    update_type=UpdateType.CREATE,
                )
                new_footnote_description.save(force_write=True)
                yield [new_footnote, new_footnote_description]

                # save footnotes
                fns = footnote_mapping.get(code, '')
                if not fns:
                    fns += f'{fn_prefix}{"{0:0=3d}".format(fn_id)}'
                else:
                    fns += f',{fn_prefix}{"{0:0=3d}".format(fn_id)}'
                footnote_mapping[code] = fns

                if fn_id == 999 and fn_prefix == 'DS':
                    fn_prefix = 'DT'
                    fn_id = 1
                elif fn_id == 999 and fn_prefix == 'DT':
                    fn_prefix = 'DV'
                    fn_id = 1
                else:
                    fn_id += 1

        # create MFN rate mapping
        mfn_rate_mapping = {}
        for row in mfn_rates:
            code = str(row[0].value)
            mfn_rate_components = blank(row[3].value.split(' & ')[0], json.loads)
            mfn_rate_mapping[code] = mfn_rate_components

        # split measures in a 0% and MFN% rate measure with footnotes, additional_codes
        logger.debug(str(footnote_mapping))
        new_measures = []
        for measure1, measure2 in zip(
            [OldMeasureRow(row) for row in old_measures2],
            [OldMeasureRow(row) for row in old_measures3],
        ):
            footnotes = parse_list(footnote_mapping.get(measure1.goods_nomenclature.item_id, ''))
            if measure1.additional_code_sid:
                logger.debug(f'already has additional code: {measure1.goods_nomenclature.item_id}')
                raise Exception
                continue
            if not footnotes:
                logger.debug(f'no footnotes found for code: {measure1.goods_nomenclature.item_id}')
                raise Exception
                continue
            # create measure with existing duty and corresponding additional code
            measure1.measure_sid = None
            measure1.footnotes = footnotes + ['EU001'] if measure1.measure_type == '115' else footnotes
            measure1.additional_code_sid = AdditionalCode.objects.current().get(
                type=add_code_type_2,
                code=add_code_mappings_dict[measure1.duty_expression]
            ).sid
            new_measures.append(measure1)

            # create no duty applies measure with MFN rate
            measure2.measure_sid = None
            measure2.footnotes = footnotes + ['EU001'] if measure1.measure_type == '115' else footnotes
            measure2.duty_component_parts = mfn_rate_mapping[measure1.goods_nomenclature.item_id]
            measure2.duty_condition_parts = None
            measure2.additional_code_sid = '14003'
            new_measures.append(measure2)

        # create new measures
        yield from self.process_measure_sheet(
            measure_creator,
            measure_ender,
            new_measures,
            raw=True
        )

    def create_transactions_tops153(self, measure_creator, measure_ender, data, transaction, counters):

        yield from self.process_measure_sheet(
            measure_creator,
            measure_ender,
            data,
        )

    def create_transactions_tops154(self, measure_creator, measure_ender, data, transaction, counters):
        cert_1_desc = CertificateDescription(
            sid=counters['certificate_description_sid_counter'](),
            description='Origin declaration stating UK origin, in the context of the Canada-UK Trade Agreement.',
            described_certificate=Certificate.objects.current().get(
                sid='088',
                certificate_type=CertificateType.objects.current().get(
                    sid='U'
                ),

            ),
            valid_between=BREXIT_TO_INFINITY,
            transaction=transaction,
            update_type=UpdateType.CREATE
        )
        yield [cert_1_desc]

    def create_transactions_tops86(self, measure_creator, measure_ender, existing_measures, transaction, counters):
        cert_1_desc = CertificateDescription(
            sid=counters['certificate_description_sid_counter'](),
            description='Catch Certificate not required - see footnote for exempted goods.',
            described_certificate=Certificate.objects.current().get(
                sid='927',
                certificate_type=CertificateType.objects.current().get(
                    sid='Y'
                ),

            ),
            valid_between=BREXIT_TO_INFINITY,
            transaction=transaction,
            update_type=UpdateType.CREATE
        )
        yield [cert_1_desc]

        footnotes = [
            ('422',	'Exempt from licence control if aquaculture products obtained from fry or larvae.'),
            ('564',	'Exempt from licence control if livers, roes, tongues, cheeks, heads and wings.'),
            ('588',	'Exempt from licence control if live ornamental fish.'),
            ('652',	'Exempt from licence control if caught in freshwater.'),
            ('723',	'Exempt from licence control if flours, meals and pellets, fit for human consumption: Of crustaceans; Of fish.'),
            ('726',	'Exempt from licence control if: Other aquatic invertebrates other than crustaceans and those molluscs specified or included in subheadings 0307 10 10 to 0307 60 00, except Illex spp., cuttlefish of the species Sepia pharaonis and sea snails of the species Strombus, live (other than ornamental), fresh or chilled.'),
        ]

        for id, description in footnotes:
            new_footnote = Footnote.objects.create(
                footnote_type=FootnoteType.objects.current().get(
                    footnote_type_id='CD'
                ),
                footnote_id=id,
                valid_between=BREXIT_TO_INFINITY,
                transaction=transaction,
                update_type=UpdateType.CREATE,
            )
            new_footnote_description = FootnoteDescription.objects.create(
                description_period_sid=counters["footnote_description_sid_counter"](),
                described_footnote=new_footnote,
                description=description,
                valid_between=BREXIT_TO_INFINITY,
                transaction=transaction,
                update_type=UpdateType.CREATE,
            )
            yield list([new_footnote, new_footnote_description])

        # 422: ex ch3, ex 1604, ex 1605
        # 564: ex ch3, ex 1605
        # 588: ex 03011000, ex 03062990, ex 03063100, ex 03063210, ex 03063310, ex 03063400, ex 03063610, ex 03063650, ex 03063690, ex 03074100, ex 03075100
        # 652: ex 03019100, ex 03019200, ex 03019300, ex 03019911, ex 03021100, ex 03021300, ex 03021900, ex 03027400, ex 03031100, ex 03031200, ex 03031300, ex 03031400, ex 03031900, ex 03032500, ex 03032600, ex 03043300, ex 03044100, ex 03044210, ex 03046200, ex 03046300, ex 03048100, ex 03048210, ex 03049921, ex 03053910, ex 03053990, ex 03054100, ex 03054300, ex 03054410, ex 03054980, ex 03055390, ex 03056950, ex 03056980, ex 16041100, ex 16041910, ex 16041991, ex 16042010, ex 16042030, ex 16054000 ex 03044290, ex 03048290
        # 723: ex 03061990, ex 03062990, ex 03051000
        # 726: ex 03079100
        def create_association(measure, footnote_id):
            new_fn = Footnote.objects.current().get(
                footnote_id=footnote_id, footnote_type__footnote_type_id='CD'
            )
            association = FootnoteAssociationMeasure(
                footnoted_measure=measure,
                associated_footnote=new_fn,
                update_type=UpdateType.CREATE,
                transaction=transaction,
            )
            yield [association]

        for row in (OldMeasureRow(row) for row in existing_measures):
            measure = Measure.objects.current().get(
                sid=row.measure_sid
            )
            # create new footnote associations
            if row.goods_nomenclature.item_id.startswith(("03", "1604", "1605")):
                yield from create_association(measure, '422')
            if row.goods_nomenclature.item_id.startswith(("03", "1605")):
                yield from create_association(measure, '564')
            if row.goods_nomenclature.item_id.startswith(
                ('03011000',
                 '03062990',
                 '03063100',
                 '03063210',
                 '03063310',
                 '03063400',
                 '03063610',
                 '03063650',
                 '03063690',
                 '03074100',
                 '03075100')):
                yield from create_association(measure, '588')
            if row.goods_nomenclature.item_id.startswith(
                ('03019100',
                '03019200',
                '03019300',
                '03019911',
                '03021100',
                '03021300',
                '03021900',
                '03027400',
                '03031100',
                '03031200',
                '03031300',
                '03031400',
                '03031900',
                '03032500',
                '03032600',
                '03043300',
                '03044100',
                '03044210',
                '03046200',
                '03046300',
                '03048100',
                '03048210',
                '03049921',
                '03053910',
                '03053990',
                '03054100',
                '03054300',
                '03054410',
                '03054980',
                '03055390',
                '03056950',
                '03056980',
                '16041100',
                '16041910',
                '16041991',
                '16042010',
                '16042030',
                '16054000',
                '03044290',
                '03048290')):
                yield from create_association(measure, '652')
            if row.goods_nomenclature.item_id.startswith(('03061990', '03062990', '03051000')):
                yield from create_association(measure, '723')
            if row.goods_nomenclature.item_id.startswith(('03079100')):
                yield from create_association(measure, '726')

    def create_transactions_tops155(self, measure_creator, measure_ender, existing_measures, transaction, counters):
        existing_measures = list(existing_measures)

        # delete first measure
        row1 = existing_measures[0]
        yield from self.process_measure_sheet(
            measure_creator,
            measure_ender,
            [row1]
        )

        # change footnotes remaining measures
        row2 = existing_measures[1]
        fn_075 = Footnote.objects.current().get(
            footnote_id='075', footnote_type__footnote_type_id='DS'
        )
        measure_2700 = Measure.objects.current().get(
            sid=int(row2[7].value)
        )
        association = FootnoteAssociationMeasure(
            footnoted_measure=measure_2700,
            associated_footnote=fn_075,
            update_type=UpdateType.DELETE,
            transaction=transaction,
        )
        yield [association]

        row3 = existing_measures[2]
        fn_038 = Footnote.objects.current().get(
            footnote_id='038', footnote_type__footnote_type_id='DS'
        )
        measure_2702 = Measure.objects.current().get(
            sid=int(row3[7].value)
        )
        association = FootnoteAssociationMeasure(
            footnoted_measure=measure_2702,
            associated_footnote=fn_038,
            update_type=UpdateType.DELETE,
            transaction=transaction,
        )
        yield [association]

    def create_transactions_tops107(self, measure_creator, measure_ender, existing_measures, transaction_model, counters):

            # Change description of CD603
            footnote = Footnote.objects.current().get(
                footnote_type=FootnoteType.objects.get(
                    footnote_type_id='CD',
                ),
                footnote_id='603'
            )
            new_footnote_description = FootnoteDescription.objects.create(
                description_period_sid=counters["footnote_description_sid_counter"](),
                described_footnote=footnote,
                description='Seal products may only be placed on the market when accompanied by an attesting document or written notification of import and a document giving evidence of where the products were acquired (Commission Implementing <a href="https://www.legislation.gov.uk/eur/2015/1850">Regulation (EU) 2015/1850 as retained in UK law</a>).',
                valid_between=BREXIT_TO_INFINITY,
                transaction=transaction_model,
                update_type=UpdateType.CREATE,
            )
            yield [new_footnote_description]

            # End date CD604
            footnote = Footnote.objects.current().get(
                footnote_type=FootnoteType.objects.get(
                    footnote_type_id='CD',
                ),
                footnote_id='604'
            )
            footnote.valid_between = DateTimeTZRange(
                footnote.valid_between.lower,
                BREXIT
            )
            footnote.transaction = transaction_model
            footnote.update_type = UpdateType.UPDATE
            yield [footnote]

            # create new footnote
            new_footnote = Footnote.objects.create(
                footnote_type=FootnoteType.objects.current().get(
                    footnote_type_id='CD'
                ),
                footnote_id='730',
                valid_between=BREXIT_TO_INFINITY,
                transaction=transaction_model,
                update_type=UpdateType.CREATE,
            )
            new_footnote_description = FootnoteDescription.objects.create(
                description_period_sid=counters["footnote_description_sid_counter"](),
                described_footnote=new_footnote,
                description='''Seal products being imported to be placed on the UK market are controlled by <a href="https://www.legislation.gov.uk/eur/2015/1850">Regulation (EU) 2015/1850 as retained in UK law</a>. Listed goods require documentary evidence before import is allowed. Certificates C679, C680 or C683 may apply. Goods not listed in this regulation are exempt from the Certification requirements. If the documentation presented for verification contains references to the European Union or the Union’s market, it may nevertheless be verified. In such cases, the words "EUROPEAN UNION" and "UNION'S MARKET" should be struck out on verification, substituting (respectively) "UNITED KINGDOM" and "MARKET IN THE UNITED KINGDOM", and these amendments should be initialled.''',
                valid_between=BREXIT_TO_INFINITY,
                transaction=transaction_model,
                update_type=UpdateType.CREATE,
            )
            yield list([new_footnote, new_footnote_description])

            # change cert Y032
            cert_1_desc = CertificateDescription(
                sid=counters['certificate_description_sid_counter'](),
                description='Goods other than seal products listed in <a href="https://www.legislation.gov.uk/eur/2015/1850">Regulation (EU) 2015/1850 as retained in UK law</a>.',
                described_certificate=Certificate.objects.current().get(
                    sid='032',
                    certificate_type=CertificateType.objects.current().get(
                        sid='Y'
                    ),

                ),
                valid_between=BREXIT_TO_INFINITY,
                transaction=transaction_model,
                update_type=UpdateType.CREATE
            )
            yield [cert_1_desc]

            # change cert C679
            cert_1_desc = CertificateDescription(
                sid=counters['certificate_description_sid_counter'](),
                description='Attesting Document (seal product), issued by a recognised body in accordance with UK regulations [<a href="https://www.legislation.gov.uk/eur/2015/1850">Regulation (EU) 2015/1850 as retained in UK law</a>].',
                described_certificate=Certificate.objects.current().get(
                    sid='679',
                    certificate_type=CertificateType.objects.current().get(
                        sid='C'
                    ),

                ),
                valid_between=BREXIT_TO_INFINITY,
                transaction=transaction_model,
                update_type=UpdateType.CREATE
            )
            yield [cert_1_desc]

            # change cert C680
            cert_1_desc = CertificateDescription(
                sid=counters['certificate_description_sid_counter'](),
                description='Written notification of import and document giving evidence where the seal products were acquired.',
                described_certificate=Certificate.objects.current().get(
                    sid='680',
                    certificate_type=CertificateType.objects.current().get(
                        sid='C'
                    ),

                ),
                valid_between=BREXIT_TO_INFINITY,
                transaction=transaction_model,
                update_type=UpdateType.CREATE
            )
            yield [cert_1_desc]

            # change cert C682
            cert_1_desc = CertificateDescription(
                sid=counters['certificate_description_sid_counter'](),
                description='Attesting document for seal products resulting from hunt by Inuit or other indigenous communities for placing on the UK market in accordance with UK regulations [Article 3 (1) of <a href="https://www.legislation.gov.uk/eur/2009/1007">Regulation (EC) No 1007/2009 on trade in seal products as retained in UK law</a>].',
                described_certificate=Certificate.objects.current().get(
                    sid='683',
                    certificate_type=CertificateType.objects.current().get(
                        sid='C'
                    ),

                ),
                valid_between=BREXIT_TO_INFINITY,
                transaction=transaction_model,
                update_type=UpdateType.CREATE
            )
            yield [cert_1_desc]

            yield from self.process_measure_sheet(
                measure_creator,
                measure_ender,
                existing_measures
            )

    def create_transactions_tops160(self, measure_creator, measure_ender, data, transaction_model,
                                   counters):
        cc_operations = data['tops-160a']
        cc_measures = data['tops-160b']
        yield from update_commodity_codes.Command().create_transactions(
            measure_creator, measure_ender, cc_operations, cc_measures, transaction_model, auto_migrate=False
        )

    def create_transactions_tops162(self, measure_creator, measure_ender, measures, transaction, counters):
        measures1, measures2 = tee(measures)
        processed = set()
        for row in measures2:
            origins = QuotaOrderNumberOrigin.objects.filter(
                order_number=QuotaOrderNumber.objects.current().get(
                    order_number=blank(row[15].value, str)
                ),
                geographical_area=GeographicalArea.objects.current().get(
                    sid=blank(row[13].value, str)
                )
            ).all()
            for origin in origins:
                if origin.sid in processed:
                    continue
                processed.add(origin.sid)
                origin.sid = counters['order_number_origin_sid_counter']()
                origin.transaction = transaction
                origin.update_type = UpdateType.CREATE
                yield [origin]

        yield from self.process_measure_sheet(
            measure_creator,
            measure_ender,
            measures1,
        )

    def create_transactions_tops158(self, measure_creator, measure_ender, new_measures, transaction, counters):
        yield from self.process_measure_sheet(
            measure_creator,
            measure_ender,
            new_measures
        )

    def create_transactions_tops163(self, measure_creator, measure_ender, data, transaction, counters):

        yield from self.process_measure_sheet(
            measure_creator,
            measure_ender,
            data,
        )

    def create_transactions_tops165(self, measure_creator, measure_ender, data, transaction, counters):

        yield from self.process_measure_sheet(
            measure_creator,
            measure_ender,
            data,
            new_start_date=datetime(2021, 5, 20)
        )

    def create_transactions_tops137(self, measure_creator, measure_ender, data, transaction, counters):
        # Change description of CD659
        footnote = Footnote.objects.current().get(
            footnote_type=FootnoteType.objects.get(
                footnote_type_id='CD',
            ),
            footnote_id='659'
        )
        new_footnote_description = FootnoteDescription.objects.create(
            description_period_sid=counters["footnote_description_sid_counter"](),
            described_footnote=footnote,
            description='The application of the individual duty rate for this company shall be conditional upon presentation to the customs authorities of the United Kingdom of a valid commercial invoice, in which must appear a declaration signed by an officer of the entity issuing the commercial invoice, in the following format:<br>(1) the name and function of the official of the entity issuing the commercial invoice;<br>(2) the following declaration:<br>"I, the undersigned, certify that the (volume) of bicycles sold for export to the United Kingdom covered by this invoice was manufactured by (company name and registered seat) (additional code) in (country concerned). I declare that the information provided in this invoice is complete and correct.<br>Date and signature".<br>If no such invoice is presented, the duty rate applicable to all other companies shall apply.',
            valid_between=BREXIT_TO_INFINITY,
            transaction=transaction,
            update_type=UpdateType.CREATE,
        )
        yield [new_footnote_description]

        yield from self.process_measure_sheet(
            measure_creator,
            measure_ender,
            data,
        )

        # End date TM882
        footnote = Footnote.objects.current().get(
            footnote_type=FootnoteType.objects.get(
                footnote_type_id='TM',
            ),
            footnote_id='882'
        )
        footnote.valid_between = DateTimeTZRange(
            footnote.valid_between.lower,
            BREXIT - timedelta(days=1)
        )
        footnote.transaction = transaction
        footnote.update_type = UpdateType.UPDATE
        yield [footnote]

    def create_transactions_tops166(self, measure_creator, measure_ender, new_measures, transaction, counters):
        yield from self.process_measure_sheet(
            measure_creator,
            measure_ender,
            new_measures
        )

    def create_transactions_tops156(self, measure_creator, measure_ender, new_measures, transaction, counters):
        yield from self.process_measure_sheet(
            measure_creator,
            measure_ender,
            new_measures
        )

    def create_transactions_tops168(self, measure_creator, measure_ender, new_measures, transaction, counters):
        yield from self.process_measure_sheet(
            measure_creator,
            measure_ender,
            new_measures,
            update=True,
        )


    def create_transactions_tops173(self, measure_creator, measure_ender, new_measures, transaction, counters):
        for order_number in ('054198', '054324', '054326'):
            quota_order_number = QuotaOrderNumber.objects.current().get(
                order_number=order_number,
            )
            quota_order_number.transaction = transaction
            quota_order_number.update_type = UpdateType.DELETE

            existing_origin = QuotaOrderNumberOrigin.objects.current().get(
                order_number=quota_order_number,
            )
            existing_origin.transaction = transaction
            existing_origin.update_type = UpdateType.DELETE

            exisiting_definition = QuotaDefinition.objects.current().get(
                order_number=quota_order_number,
            )
            exisiting_definition.transaction = transaction
            exisiting_definition.update_type = UpdateType.DELETE
            yield [exisiting_definition, existing_origin, quota_order_number]

    def create_transactions_tops100(self, measure_creator, measure_ender, new_measures, transaction, counters):
        yield from self.process_measure_sheet(
            measure_creator,
            measure_ender,
            new_measures,
        )

    def create_transactions_tops16(self, measure_creator, measure_ender, quota_rows, transaction_model, counters):
        previous_order_number_sid = None
        transaction = []
        brexit_end_date = BREXIT - timedelta(days=1)
        processed_quota_definition_sids = set()
        processed_quota_order_number_origin_sids = set()
        processed_associations = set()
        NOTHING, UPDATE, DELETE = 0, 1, 2

        def action(valid_between):
            starts_after_brexit = valid_between.lower.replace(tzinfo=None) >= BREXIT
            ends_before_brexit = (valid_between.upper and valid_between.upper.replace(tzinfo=None) < BREXIT)
            if starts_after_brexit:
                return DELETE
            elif ends_before_brexit:
                return NOTHING
            else:
                return UPDATE

        for i, row in enumerate(quota_rows):
            logger.debug(f"row: {i}")
            quota_order_number_sid = int(row[0].value)
            quota_order_number_origin_sid = int(row[3].value) if row[3].value else None
            quota_definition_sid = int(row[6].value) if row[6].value else None

            # close previous order number as latest action when transitioning to new order number
            # and reset transaction queue (never has end-date)
            if previous_order_number_sid and quota_order_number_sid != previous_order_number_sid:
                order_number = QuotaOrderNumber.objects.current().get(
                    sid=previous_order_number_sid,
                )
                if action(order_number.valid_between) == DELETE:
                    order_number.update_type = UpdateType.DELETE
                else:    # update (no cases where end-dates)
                    order_number.update_type = UpdateType.UPDATE
                    order_number.valid_between = DateTimeTZRange(
                        order_number.valid_between.lower,
                        brexit_end_date
                    )
                order_number.transaction = transaction_model
                transaction.append(order_number)
                yield transaction
                transaction = []

            # include associated quota definitions/associations/blocking periods/suspension periods
            # in the current order number transaction queue
            if quota_definition_sid and quota_definition_sid not in processed_quota_definition_sids:
                definition = QuotaDefinition.objects.current().get(
                    sid=quota_definition_sid,
                )
                if action(definition.valid_between) == DELETE:
                    # remove any linked quota associations
                    main_associations = QuotaAssociation.objects.current().filter(
                        main_quota=definition
                    ).all()
                    sub_associations = QuotaAssociation.objects.current().filter(
                        sub_quota=definition
                    ).all()
                    for association in main_associations | sub_associations:
                        sids = (association.main_quota.sid, association.sub_quota.sid)
                        if sids not in processed_associations:
                            association.update_type = UpdateType.DELETE
                            association.transaction = transaction_model
                            transaction.append(association)
                            processed_associations.add(sids)

                    # remove any linked quota blocking periods
                    blocking_periods = QuotaBlocking.objects.current().filter(
                        quota_definition=definition
                    ).all()
                    for blocking_period in blocking_periods:
                        blocking_period.update_type = UpdateType.DELETE
                        blocking_period.transaction = transaction_model
                        transaction.append(blocking_period)

                    # remove any linked quota suspension periods
                    suspension_periods = QuotaSuspension.objects.current().filter(
                        quota_definition=definition
                    ).all()
                    for suspension_period in suspension_periods:
                        suspension_period.update_type = UpdateType.DELETE
                        suspension_period.transaction = transaction_model
                        transaction.append(suspension_period)

                    definition.update_type = UpdateType.DELETE
                    definition.transaction = transaction_model
                    transaction.append(definition)

                elif action(definition.valid_between) == UPDATE:
                    # remove any linked quota blocking periods after brexit
                    blocking_periods = QuotaBlocking.objects.current().filter(
                        quota_definition=definition
                    ).all()
                    for blocking_period in blocking_periods:
                        if action(blocking_period.valid_between) == DELETE:
                            blocking_period.update_type = UpdateType.DELETE
                            blocking_period.transaction = transaction_model
                            transaction.append(blocking_period)
                        elif action(blocking_period.valid_between) == UPDATE:
                            pass    # never happens no implementation required

                    # remove any linked quota suspension periods after brexit
                    suspension_periods = QuotaSuspension.objects.current().filter(
                        quota_definition=definition
                    ).all()
                    for suspension_period in suspension_periods:
                        if action(suspension_period.valid_between) == DELETE:
                            suspension_period.update_type = UpdateType.DELETE
                            suspension_period.transaction = transaction_model
                            transaction.append(suspension_period)
                        elif action(suspension_period.valid_between) == UPDATE:
                            pass    # never happens no implementation required

                    definition.update_type = UpdateType.UPDATE
                    definition.valid_between = DateTimeTZRange(
                        definition.valid_between.lower,
                        brexit_end_date
                    )
                    definition.transaction = transaction_model
                    transaction.append(definition)

                processed_quota_definition_sids.add(quota_definition_sid)

            # include origins in the current order number transaction queue
            if quota_order_number_origin_sid \
                    and quota_order_number_origin_sid not in processed_quota_order_number_origin_sids:
                order_number_origin = QuotaOrderNumberOrigin.objects.current().get(
                    sid=quota_order_number_origin_sid,
                )
                if action(order_number_origin.valid_between) == DELETE:

                    # remove any linked exclusions
                    excluded_areas = QuotaOrderNumberOriginExclusion.objects.current().filter(
                        origin=order_number_origin
                    ).all()
                    for area in excluded_areas:
                        area.update_type = UpdateType.DELETE
                        area.transaction = transaction_model
                        transaction.append(area)

                    order_number_origin.update_type = UpdateType.DELETE

                else:      # update (no cases where end-dates)
                    order_number_origin.update_type = UpdateType.UPDATE
                    order_number_origin.valid_between = DateTimeTZRange(
                        order_number_origin.valid_between.lower,
                        brexit_end_date
                    )
                order_number_origin.transaction = transaction_model
                transaction.append(order_number_origin)
                processed_quota_order_number_origin_sids.add(quota_order_number_origin_sid)

            previous_order_number_sid = quota_order_number_sid

        # finally flush latest transaction queue as not included in the loop
        if previous_order_number_sid:
            order_number = QuotaOrderNumber.objects.current().get(
                sid=previous_order_number_sid,
            )
            if action(order_number.valid_between) == DELETE:
                order_number.update_type = UpdateType.DELETE
            else:   # update (no cases where end-dates)
                order_number.update_type = UpdateType.UPDATE
                order_number.valid_between = DateTimeTZRange(
                    order_number.valid_between.lower,
                    brexit_end_date
                )
            order_number.transaction = transaction_model
            transaction.append(order_number)
        yield transaction

    def create_transactions_tops131(self, measure_creator, measure_ender, new_measures, transaction, counters):
        yield from self.process_measure_sheet(
            measure_creator,
            measure_ender,
            new_measures,
        )

    def create_transactions_tops178(self, measure_creator, measure_ender, new_measures, transaction, counters):
        yield from self.process_measure_sheet(
            measure_creator,
            measure_ender,
            new_measures,
        )

        cert = Certificate.objects.current().get(
            sid='050',
            certificate_type=CertificateType.objects.current().get(
                sid='C'
            ),
        )
        cert.valid_between = DateTimeTZRange(
            cert.valid_between.lower,
            BREXIT - timedelta(days=1)
        )
        cert.transaction = transaction
        cert.update_type = UpdateType.UPDATE
        yield [cert]

    def create_transactions_tops181(self, measure_creator, measure_ender, data, transaction_model,
                                   counters):
        cc_operations = data['tops-181a']
        cc_measures = data['tops-181b']
        new_measures = data['tops-181c']
        yield from update_commodity_codes.Command().create_transactions(
            measure_creator, measure_ender, cc_operations, cc_measures, transaction_model, auto_migrate=False
        )

        yield from self.process_measure_sheet(
            measure_creator,
            measure_ender,
            new_measures,
        )

    def create_transactions_tops182(self, measure_creator, measure_ender, measures, transaction, counters):
        measures1, measures2 = tee(measures)
        processed = set()
        for row in measures2:
            origins = QuotaOrderNumberOrigin.objects.filter(
                order_number=QuotaOrderNumber.objects.current().get(
                    order_number=blank(row[15].value, str)
                ),
                geographical_area=GeographicalArea.objects.current().get(
                    sid=blank(row[13].value, str)
                )
            ).all()
            for origin in origins:
                if origin.sid in processed:
                    continue
                processed.add(origin.sid)
                origin.sid = counters['order_number_origin_sid_counter']()
                origin.transaction = transaction
                origin.update_type = UpdateType.CREATE
                yield [origin]

        yield from self.process_measure_sheet(
            measure_creator,
            measure_ender,
            measures1,
        )

    def create_transactions_tops126(self, measure_creator, measure_ender, measures, transaction, counters):
        cert_1_desc = CertificateDescription(
            sid=counters['certificate_description_sid_counter'](),
            description='Certificate of Inspection for Organic Products as referred to in Article 33(1)(d) of <a href="https://www.legislation.gov.uk/eur/2007/834">Regulation (EC) No 834/2007</a> as retained in UK law.',
            described_certificate=Certificate.objects.current().get(
                sid='644',
                certificate_type=CertificateType.objects.current().get(
                    sid='C'
                ),

            ),
            valid_between=BREXIT_TO_INFINITY,
            transaction=transaction,
            update_type=UpdateType.CREATE
        )
        yield [cert_1_desc]

        cert_1_desc = CertificateDescription(
            sid=counters['certificate_description_sid_counter'](),
            description='Goods not covered by <a href="https://www.legislation.gov.uk/eur/2007/834">Regulation (EC) No 834/2007</a> (e.g. non organic goods) as retained in UK Law.',
            described_certificate=Certificate.objects.current().get(
                sid='929',
                certificate_type=CertificateType.objects.current().get(
                    sid='Y'
                ),

            ),
            valid_between=BREXIT_TO_INFINITY,
            transaction=transaction,
            update_type=UpdateType.CREATE
        )
        yield [cert_1_desc]

        yield from self.process_measure_sheet(
            measure_creator,
            measure_ender,
            measures,
            update=True,
        )

    def create_transactions_tops185(self, measure_creator, measure_ender, measures, transaction, counters):
        yield from self.process_measure_sheet(
            measure_creator,
            measure_ender,
            measures,
            update=True,
        )

    def create_transactions_tops103(self, measure_creator, measure_ender, data, transaction, counters):
        measures = data['tops-103a']
        footnotes = data['tops-103b']
        mfn_rates = data['tops-103d']
        existing_mfn_measures = data['tops-103c']

        old_measures, measures_copy = tee(measures)
        old_measures2, old_measures3 = tee(measures_copy)

        # change description
        add_code_desc = AdditionalCodeDescription.objects.current().get(
            description_period_sid='11004'
        )
        add_code_desc.description = 'Partial duty suspension applies - see footnote for coverage. Please do not use if the MFN import duty rate is 0%.'
        add_code_desc.transaction = transaction
        add_code_desc.update_type = UpdateType.UPDATE
        yield [add_code_desc]

        # delete old measures
        yield from self.process_measure_sheet(
            measure_creator,
            measure_ender,
            old_measures,
        )

        # delete existing mfn rates rates
        yield from self.process_measure_sheet(
            measure_creator,
            measure_ender,
            existing_mfn_measures,
        )

        # remove permission for additional code 2 to be applied on measure type 112
        add_code_measure_type_mapping = AdditionalCodeTypeMeasureType.objects.current().get(
            measure_type=MeasureType.objects.current().get(
                 sid='112',
            ),
            additional_code_type=AdditionalCodeType.objects.get(
                 sid='2',
            ),
        )
        add_code_measure_type_mapping.transaction = transaction
        add_code_measure_type_mapping.update_type = UpdateType.DELETE
        yield [add_code_measure_type_mapping]

        # create footnotes and mapping
        footnote_mapping = {}
        fn_id = 76
        fn_prefix = 'DS'
        existing_footnotes = {
            '2903740000': '002',
            '2905490000': '003',
            '2909500090': '004',
            '2914500090': '005',
            '2914790090': '006',
            '2915907090': '007',
            '2916399090': '008',
            '2920290090': '009',
            '2920901090': '010',
            '2921420090': '011',
            '2921430090': '012',
            '2921490090': '013',
            '2921511990': '014',
            '2921599090': '015',
            '2922290090': '016',
            '2922390090': '017',
            '2924190090': '018',
            '2924297099': '019',
            '2926907090': '020',
            '2930909899': '021',
            '2931399090': '022',
            '2931900090': '023',
            '2932190090': '024',
            '2932990090': '025',
            '2933199090': '026',
            '2933499090': '027',
            '2934999090': '028',
            '2935909099': '029',
            '3204170090': '030',
            '3204190090': '031',
            '3208101000': '032',
            '3215110000': '033',
            '3215190090': '034',
            '3402901090': '035',
            '3808939090': '036',
            '3808999090': '037',
            '3824999299': '038',
            '3901908099': '039',
            '3903909060': '040',
            '3906909090': '041',
            '3907100090': '042',
            '3907998090': '043',
            '3908900090': '044',
            '3919908099': '045',
            '3921905590': '046',
            '3926300090': '047',
            '8108200090': '048',
            '8108906090': '049',
            '8414592590': '050',
            '8507600090': '051',
            '8507903090': '052',
            '8507908099': '053',
            '8528590090': '054',
            '8535900089': '055',
            '8535900090': '055',
            '8537109899': '056',
            '8543709099': '057',
            '8708802090': '058',
            '8708809110': '059',
            '8708809120': '059',
            '8708809190': '059',
            '9401908090': '060',
        }
        # already updated in previous tickets
        updated_descriptions = ['DS010', 'DS038', 'DS055']
        for row in footnotes:
            code = str(row[0].value)
            # already done in previous ticket
            # if code in (
            #     '3824999299',
            #     '2920901090',
            #     '2932190090',
            #     '2933399990',
            #     '3921190099',
            #     '3926909790',
            #     '4016930090',
            #     '5603149090',
            #     '6909190090',
            #     '7604291090',
            #     '8108903090',
            #     '8409990090',
            #     '8414808090',
            #     '8415900099',
            #     '8535900089',
            #     '8708809100',
            # ):
            #     continue

            # only create footnotes for the commodities
            # where suspension applies to subset of code
            if code not in (
                '2811198090',
                '2903740000',
                '2905490000',
                '2909500090',
                '2914500090',
                '2914790090',
                '2915907090',
                '2916399090',
                '2920290090',
                '2920901090',
                '2921420090',
                '2921430090',
                '2921490090',
                '2921511990',
                '2921599090',
                '2922290090',
                '2922390090',
                '2924297099',
                '2930909899',
                '2931399090',
                '2931900090',
                '2932190090',
                '2932990090',
                '2933399990',
                '2933499090',
                '3204170090',
                '3204190090',
                '3215190090',
                '3402901090',
                '3808939090',
                '3808999090',
                '3824999299',
                '3901908099',
                '3903909090',
                '3906909090',
                '3907100090',
                '3908900090',
                '3919908099',
                '3921190099',
                '3921905590',
                '3926300090',
                '3926909790',
                '4016930090',
                '5603149090',
                '6909190090',
                '7604291090',
                '8108200090',
                '8108903090',
                '8108906090',
                '8409990090',
                '8414592590',
                '8414808090',
                '8415900099',
                '8507600090',
                '8507903090',
                '8507908099',
                '8535900089',
                '8537109899',
                '8543709099',
                '8708809100',
            ):
                continue

            description = str(row[2].value)
            if code in existing_footnotes.keys():
                if existing_footnotes[code] not in updated_descriptions:
                    footnote = Footnote.objects.current().get(
                        footnote_type=FootnoteType.objects.get(
                            footnote_type_id='DS',
                        ),
                        footnote_id=existing_footnotes[code],
                    )
                    footnote_description = FootnoteDescription.objects.current().get(
                        described_footnote=footnote
                    )
                    footnote_description.update_type = UpdateType.UPDATE
                    footnote_description.transaction = transaction
                    footnote_description.description = description
                    yield [footnote_description]
                    updated_descriptions.append(existing_footnotes[code])
                else:
                    logger.debug(f'Description for DS{footnote.footnote_id} already updated')
                footnote_mapping[code] = f'DS{footnote.footnote_id}'

            else:
                new_footnote = Footnote.objects.create(
                    footnote_type=FootnoteType.objects.current().get(
                        footnote_type_id=fn_prefix
                    ),
                    footnote_id="{0:0=3d}".format(fn_id),
                    valid_between=BREXIT_TO_INFINITY,
                    transaction=transaction,
                    update_type=UpdateType.CREATE,
                )
                new_footnote.save(force_write=True)
                new_footnote_description = FootnoteDescription.objects.create(
                    description_period_sid=counters["footnote_description_sid_counter"](),
                    described_footnote=new_footnote,
                    description=description,
                    valid_between=BREXIT_TO_INFINITY,
                    transaction=transaction,
                    update_type=UpdateType.CREATE,
                )
                new_footnote_description.save(force_write=True)
                yield [new_footnote, new_footnote_description]

                # save footnotes
                fns = footnote_mapping.get(code, '')
                if not fns:
                    fns += f'{fn_prefix}{"{0:0=3d}".format(fn_id)}'
                else:
                    fns += f',{fn_prefix}{"{0:0=3d}".format(fn_id)}'
                footnote_mapping[code] = fns

                fn_id += 1

        # create MFN rate mapping
        mfn_rate_mapping = {}
        for row in mfn_rates:
            code = str(row[0].value)
            mfn_rate_components = blank(row[3].value.split(' & ')[0], json.loads)
            mfn_rate_mapping[code] = mfn_rate_components

        # split measures in a 0% and MFN% rate measure with footnotes, additional_codes
        logger.debug(str(footnote_mapping))
        new_measures = []
        for measure1, measure2 in zip(
            [OldMeasureRow(row) for row in old_measures2],
            [OldMeasureRow(row) for row in old_measures3],
        ):
            footnotes = parse_list(footnote_mapping.get(measure1.goods_nomenclature.item_id, ''))
            if measure1.additional_code_sid:
                logger.debug(f'already has additional code: {measure1.goods_nomenclature.item_id}')
                # move to 103/105 type
                measure1.measure_sid = None
                # TM861 already included in descriptions
                if 'TM861' in measure1.footnotes:
                    measure1.footnotes.remove('TM861')
                measure1.measure_type = '103'
                measure1.measure_end_date = None
                new_measures.append(measure1)
                continue

            if not footnotes:
                logger.debug(f'no footnotes found for code: {measure1.goods_nomenclature.item_id}')
                raise Exception

            # create measure with existing duty and corresponding additional code
            measure1.measure_sid = None
            measure1.footnotes = footnotes + ['EU001'] if measure1.measure_type == '115' else footnotes
            measure1.measure_type = '103'
            measure1.measure_end_date = None
            measure1.additional_code_sid = '14002'
            new_measures.append(measure1)

            # create no duty applies measure with MFN rate
            measure2.measure_sid = None
            measure2.footnotes = footnotes + ['EU001'] if measure1.measure_type == '115' else footnotes
            measure2.measure_type = '103'
            measure2.measure_end_date = None
            measure2.duty_component_parts = mfn_rate_mapping[measure1.goods_nomenclature.item_id]
            measure2.duty_condition_parts = None
            measure2.additional_code_sid = '14003'
            new_measures.append(measure2)

        # create new measures
        yield from self.process_measure_sheet(
            measure_creator,
            measure_ender,
            new_measures,
            raw=True
        )

    def create_transactions_tops186(self, measure_creator, measure_ender, data, transaction_model,
                                   counters):
        cc_operations = data['tops-186a']
        cc_measures = data['tops-186b']
        new_measures = data['tops-186c']
        yield from update_commodity_codes.Command().create_transactions(
            measure_creator, measure_ender, cc_operations, cc_measures, transaction_model, auto_migrate=False
        )

        yield from self.process_measure_sheet(
            measure_creator,
            measure_ender,
            new_measures,
        )

    def create_transactions_tops188(self, measure_creator, measure_ender, measures, transaction, counters):
        measures1, measures2 = tee(measures)
        processed = set()
        for row in measures2:
            origins = QuotaOrderNumberOrigin.objects.filter(
                order_number=QuotaOrderNumber.objects.current().get(
                    order_number=blank(row[15].value, str)
                ),
                geographical_area=GeographicalArea.objects.current().get(
                    sid=blank(row[13].value, str)
                )
            ).all()
            for origin in origins:
                if origin.sid in processed:
                    continue
                processed.add(origin.sid)
                origin.sid = counters['order_number_origin_sid_counter']()
                origin.transaction = transaction
                origin.update_type = UpdateType.CREATE
                yield [origin]

        yield from self.process_measure_sheet(
            measure_creator,
            measure_ender,
            measures1,
        )
