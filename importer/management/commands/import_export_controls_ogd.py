import logging
import sys
from datetime import datetime
from typing import Iterator
from typing import List

import xlrd
from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils.datastructures import OrderedSet
from psycopg2._range import DateTimeTZRange

from additional_codes.models import AdditionalCode
from common.models import TrackedModel
from common.renderers import counter_generator
from common.validators import UpdateType
from footnotes.models import Footnote
from geo_areas.models import GeographicalArea
from importer.management.commands.doc_importer import RowsImporter
from importer.management.commands.patterns import BREXIT, MeasureCreatingPatternWithExpression
from importer.management.commands.patterns import MeasureEndingPattern
from importer.management.commands.patterns import OldMeasureRow
from importer.management.commands.utils import EnvelopeSerializer, parse_duty_parts
from importer.management.commands.utils import NomenclatureTreeCollector
from importer.management.commands.utils import split_groups
from measures.models import MeasureType
from regulations.models import Group
from regulations.models import Regulation
from regulations.validators import RoleType
from workbaskets.models import WorkBasket
from workbaskets.validators import WorkflowStatus

logger = logging.getLogger(__name__)

EUR_GBP_CONVERSION_RATE = 0.83687
BREXIT_TO_INFINITY = DateTimeTZRange(BREXIT, None)
MEASURE_TYPES = [
    '277', '410',  '430', '431', '442', '447', '464',
    '465', '474', '475', '481', '482', '483', '707',
    '709', '712', '714', '730', '735', '748', '749',
    '750', '751', '755', '760', '766', '774',
]
REGULATION_MEASURE_TYPE_TRANSFER = {
    ('D140284', '277'): True,
    ('R180285', '277'): None,
    ('R140494', '277'): True,
    ('R200625', '277'): True,
    ('R120642', '277'): None,
    ('R130743', '277'): True,
    ('R150936', '277'): False,
    ('R091005', '277'): True,
    ('R171509', '277'): None,
    ('R171548', '277'): None,
    ('D070275', '410'): True,
    ('R192007', '410'): True,
    ('R970088',	'464'): True,
    ('R201336',	'464'): True,
    ('R130952', '430'): False,
    ('R130952', '431'): False,
    ('R152447', '442'): False,
    ('R152447', '447'): False,
    ('R970088', '464'): True,   # TBC that needs loading
    ('R170271', '464'): False,
    ('R090803', '464'): False,
    ('R111331', '464'): False,
    ('R201336', '464'): True,   # TBC that needs loading
    ('R172213', '464'): False,
    ('D190001', '465'): False,
    ('D060232', '465'): True,
    ('D050394', '465'): True,
    ('R050111', '465'): True,
    ('R180273', '465'): True,
    ('R070341', '465'): True,
    ('R080514', '465'): True,
    ('R080555', '465'): True,
    ('R100640', '465'): True,
    ('R080972', '465'): True,
    ('R131001', '465'): False,
    ('R081031', '465'): False,
    ('R031210', '465'): True,
    ('R161237', '465'): True,
    ('R131259', '465'): True,
    ('R081295', '465'): True,
    ('R131308', '465'): True,
    ('R131332', '465'): None,
    ('R061368', '465'): True,
    ('R071375', '465'): True,
    ('R161443', '465'): True,
    ('R171525', '465'): None,
    ('R171548', '465'): None,
    ('R021832', '465'): False,
    ('R031984', '465'): True,
    ('R152447', '465'): False,
    ('D971401', '474'): False,
    ('R150936', '474'): False,
    ('R050111', '475'): True,
    ('R810139', '475'): False,
    ('R110284', '475'): True,
    ('R110321', '475'): True,
    ('R110333', '475'): True,
    ('R200625', '475'): True,
    ('R060972', '475'): True,
    ('R091005', '475'): True,
    ('R171548', '475'): None,
    ('R022368', '475'): True,
    ('R913254', '475'): True,
    ('D980238', '481'): True,
    ('D050690', '481'): False,
    ('D030914', '481'): False,
    ('R131001', '481'): False,
    ('R141101', '481'): False,
    ('R161821', '481'): False,
    ('R120672', '482'): False,
    ('R200874', '482'): None,
    ('R180913', '482'): None,
    ('R180914', '482'): None,
    ('R120927', '482'): False,
    ('R130952', '482'): False,
    ('R150982', '482'): None,
    ('R190999', '482'): None,
    ('R161051', '482'): None,
    ('R171134', '482'): None,
    ('R121223', '482'): None,
    ('R101255', '482'): None,
    ('R131387', '482'): None,
    ('R131388', '482'): None,
    ('R181602', '482'): False,
    ('R182069', '482'): None,
    ('R152449', '482'): None,
    ('R172467', '482'): None,
    ('R120927', '483'): False,
    ('R131388', '483'): None,
    ('D140512', '707'): None,
    ('R171509', '707'): None,
    ('R120267', '709'): None,  # changing none to false as was missing in previous IC sheet
    ('R171509', '709'): None,
    ('R191262', '712'): True,
    ('R120267', '714'): None,
    ('R171509', '714'): None,
    ('R150949', '730'): True,
    ('R090116', '735'): True,
    ('R170852', '748'): True,
    ('R170852', '749'): True,
    ('R070834', '750'): True,
    ('R061013', '751'): True,
    ('R061013', '755'): True,
    ('R171509', '760'): None,
    ('D130798', '766'): None,
    ('D190854', '774'): True,
}
NEW_REGULATIONS = [
    'C2100230',
    'A1907820',
    'C2100260',
    'A1907950',
    'X1905830',
    'C2100270',
    'C2100310',
    'C2100320',
    'P1900030',
    'P1900040',
    'X1907420',
    'C2100240',
    'C2100280',
    'A1913120',
    'X2007070',
    'A1908120',
    'A1914050',
    'A1908220',
    'A1908480',
    'C2100300',
    'A1907530',
    'A1906640',
    'C2100290',
    'X1906200',
    'X1908440',
    'A1900160',
    'P1900010',
    'A1902230',
    'X1811860',
    'X1900960',
    'X1906930',
    'X1905900',
    'X1302330',
]
NEW_REGULATION_PARAMS = {
    NEW_REGULATIONS[0]: {
        'regulation_group': 'MLA',
        'published_at': datetime(2021, 1, 1),
        'approved': False,
        'valid_between': DateTimeTZRange(BREXIT, None),
        'information_text': None
    },
    NEW_REGULATIONS[1]: {
        'regulation_group': 'MLA',
        'published_at': datetime(2019, 4, 1),
        'approved': True,
        'valid_between': DateTimeTZRange(BREXIT, None),
        'information_text': (
            '''The Trade in Animals and Related Products (Amendment) (EU Exit) Regulations 2019|'''
            '''S.I. 2019/782|https://www.legislation.gov.uk/uksi/2019/782'''
        )
    },
    NEW_REGULATIONS[2]: {
        'regulation_group': 'PRS',
        'published_at': datetime(2021, 1, 1),
        'approved': False,
        'valid_between': DateTimeTZRange(BREXIT, None),
        'information_text': None
    },
    NEW_REGULATIONS[3]: {
        'regulation_group': 'MLA',
        'published_at': datetime(2019, 4, 4),
        'approved': True,
        'valid_between': DateTimeTZRange(BREXIT, None),
        'information_text': (
            '''The Import of and Trade in Animals and Animal Products (Amendment etc.) (EU Exit) Regulations 2019|'''
            '''S.I. 2019/795|https://www.legislation.gov.uk/uksi/2019/795'''
        )
    },
    NEW_REGULATIONS[4]: {
        'regulation_group': 'MLA',
        'published_at': datetime(2019, 3, 14),
        'approved': True,
        'valid_between': DateTimeTZRange(BREXIT, None),
        'information_text': (
            '''The Ozone-Depleting Substances and Fluorinated Greenhouse Gases (Amendment etc.) (EU Exit) Regulations 2019|'''
            '''S.I. 2019/583|https://www.legislation.gov.uk/uksi/2019/583'''
        )
    },
    NEW_REGULATIONS[5]: {
        'regulation_group': 'MLA',
        'published_at': datetime(2021, 1, 1),
        'approved': False,
        'valid_between': DateTimeTZRange(BREXIT, None),
        'information_text': None
    },
    NEW_REGULATIONS[6]: {
        'regulation_group': 'DUM',
        'published_at': datetime(2021, 1, 1),
        'approved': False,
        'valid_between': DateTimeTZRange(BREXIT, None),
        'information_text': None
    },
    NEW_REGULATIONS[7]: {
        'regulation_group': 'DUM',
        'published_at': datetime(2021, 1, 1),
        'approved': False,
        'valid_between': DateTimeTZRange(BREXIT, None),
        'information_text': None
    },
    NEW_REGULATIONS[8]: {
        'regulation_group': 'PRF',
        'published_at': datetime(2019, 2, 7),
        'approved': True,
        'valid_between': DateTimeTZRange(BREXIT, None),
        'information_text': (
            '''Agreement between the United Kingdom of Great Britain and Northern Ireland and the United States of America on Trade in Wine|'''
            '''USA No. 3 (2019)|https://www.gov.uk/government/publications/cs-usa-no32019-ukusa-agreement-on-trade-in-wine'''
        )
    },
    NEW_REGULATIONS[9]: {
        'regulation_group': 'PRF',
        'published_at': datetime(2019, 2, 20),
        'approved': True,
        'valid_between': DateTimeTZRange(BREXIT, None),
        'information_text': (
            '''Trade Agreement between the United Kingdom of Great Britain and Northern Ireland and the Swiss Confederation.|'''
            '''Switzerland No. 4 (2019)|https://www.gov.uk/government/publications/cs-switzerland-no42019-ukswitzerland-trade-agreement'''
        )
    },
    NEW_REGULATIONS[10]: {
        'regulation_group': 'MLA',
        'published_at': datetime(2019, 3, 28),
        'approved': True,
        'valid_between': DateTimeTZRange(BREXIT, None),
        'information_text': (
            '''The Law Enforcement and Security (Amendment) (EU Exit) Regulations 2019|'''
            '''S.I. 2019/742|https://www.legislation.gov.uk/uksi/2019/742'''
        )
    },
    NEW_REGULATIONS[11]: {
        'regulation_group': 'PRF',
        'published_at': datetime(2021, 1, 1),
        'approved': False,
        'valid_between': DateTimeTZRange(BREXIT, None),
        'information_text': None
    },
    NEW_REGULATIONS[12]: {
        'regulation_group': 'MLA',
        'published_at': datetime(2021, 1, 1),
        'approved': False,
        'valid_between': DateTimeTZRange(BREXIT, None),
        'information_text': None
    },
    NEW_REGULATIONS[13]: {
        'regulation_group': 'MLA',
        'published_at': datetime(2019, 10, 7),
        'approved': True,
        'valid_between': DateTimeTZRange(BREXIT, None),
        'information_text': (
            '''The Common Fisheries Policy and Animals (Amendment etc.) (EU Exit) Regulations 2019|'''
            '''S.I. 2019/1312|https://www.legislation.gov.uk/uksi/2019/1312'''
        )
    },
    NEW_REGULATIONS[14]: {
        'regulation_group': 'MLA',
        'published_at': datetime(2020, 7, 7),
        'approved': True,
        'valid_between': DateTimeTZRange(BREXIT, None),
        'information_text': (
            '''The Iraq (Sanctions) (EU Exit) Regulations 2020|'''
            '''S.I. 2020/707|https://www.legislation.gov.uk/uksi/2020/707'''
        )
    },
    NEW_REGULATIONS[15]: {
        'regulation_group': 'MLA',
        'published_at': datetime(2019, 4, 4),
        'approved': True,
        'valid_between': DateTimeTZRange(BREXIT, None),
        'information_text': (
            '''The Common Agricultural Policy and Market Measures (Miscellaneous Amendments) (EU Exit) Regulations 2019|'''
            '''S.I. 2019/812|https://www.legislation.gov.uk/uksi/2019/812'''
        )
    },
    NEW_REGULATIONS[16]: {
        'regulation_group': 'MLA',
        'published_at': datetime(2019, 10, 28),
        'approved': True,
        'valid_between': DateTimeTZRange(BREXIT, None),
        'information_text': (
            '''The Common Agricultural Policy and Common Organisation of the Markets in Agricultural Products (Miscellaneous Amendments) (EU Exit) Regulations 2019|'''
            '''S.I. 2019/1405|https://www.legislation.gov.uk/uksi/2019/1405'''
        )
    },
    NEW_REGULATIONS[17]: {
        'regulation_group': 'MLA',
        'published_at': datetime(2019, 4, 4),
        'approved': True,
        'valid_between': DateTimeTZRange(BREXIT, None),
        'information_text': (
            '''The Market Measures (Marketing Standards) (Amendment) (EU Exit) Regulations 2019|'''
            '''S.I. 2019/822|https://www.legislation.gov.uk/uksi/2019/822'''
        )
    },
    NEW_REGULATIONS[18]: {
        'regulation_group': 'MLA',
        'published_at': datetime(2019, 3, 28),
        'approved': True,
        'valid_between': DateTimeTZRange(BREXIT, None),
        'information_text': (
            '''The Common Fisheries Policy (Amendment etc.) (EU Exit) (No. 2) Regulations 2019|'''
            '''S.I. 2019/848|https://www.legislation.gov.uk/uksi/2019/848'''
        )
    },
    NEW_REGULATIONS[19]: {
        'regulation_group': 'MLA',
        'published_at': datetime(2021, 1, 1),
        'approved': False,
        'valid_between': DateTimeTZRange(BREXIT, None),
        'information_text': None
    },
    NEW_REGULATIONS[20]: {
        'regulation_group': 'MLA',
        'published_at': datetime(2019, 3, 28),
        'approved': True,
        'valid_between': DateTimeTZRange(BREXIT, None),
        'information_text': (
            '''The Common Fisheries Policy and Aquaculture (Amendment etc.) (EU Exit) Regulations 2019|'''
            '''S.I. 2019/753|https://www.legislation.gov.uk/uksi/2019/753'''
        )
    },
    NEW_REGULATIONS[21]: {
        'regulation_group': 'MLA',
        'published_at': datetime(2019, 3, 22),
        'approved': True,
        'valid_between': DateTimeTZRange(BREXIT, None),
        'information_text': (
            '''The Food and Feed Imports (Amendment) (EU Exit) Regulations 2019|'''
            '''S.I. 2019/664|https://www.legislation.gov.uk/uksi/2019/664'''
        )
    },
    NEW_REGULATIONS[22]: {
        'regulation_group': 'MLA',
        'published_at': datetime(2021, 1, 1),
        'approved': False,
        'valid_between': DateTimeTZRange(BREXIT, None),
        'information_text': None
    },
    NEW_REGULATIONS[23]: {
        'regulation_group': 'MLA',
        'published_at': datetime(2019, 3, 19),
        'approved': True,
        'valid_between': DateTimeTZRange(BREXIT, None),
        'information_text': (
            '''The Waste (Miscellaneous Amendments) (EU Exit) Regulations 2019|'''
            '''S.I. 2019/620|https://www.legislation.gov.uk/uksi/2019/620'''
        )
    },
    NEW_REGULATIONS[24]: {
        'regulation_group': 'MLA',
        'published_at': datetime(2019, 3, 5),
        'approved': True,
        'valid_between': DateTimeTZRange(BREXIT, None),
        'information_text': (
            '''The Kimberley Process Certification Scheme (Amendment) (EU Exit) Regulations 2019|'''
            '''S.I. 2019/844|https://www.legislation.gov.uk/uksi/2019/844'''
        )
    },
    NEW_REGULATIONS[25]: {
        'regulation_group': 'MLA',
        'published_at': datetime(2019, 1, 8),
        'approved': True,
        'valid_between': DateTimeTZRange(BREXIT, None),
        'information_text': (
            '''The Leghold Trap and Pelt Imports (Amendment etc.) (EU Exit) Regulations 2019|'''
            '''S.I. 2019/16|https://www.legislation.gov.uk/uksi/2019/16'''
        )
    },
    NEW_REGULATIONS[26]: {
        'regulation_group': 'PRF',
        'published_at': datetime(2019, 10, 25),
        'approved': True,
        'valid_between': DateTimeTZRange(BREXIT, None),
        'information_text': (
            '''Agreement establishing an Association between the United Kingdom of Great Britain and Northern Ireland and the Republic of Tunisia.|'''
            '''Tunisia No. 1 (2019)|https://www.gov.uk/government/publications/cs-tunisia-no12019-uktunisia-agreement-establishing-an-association'''
        )
    },
    NEW_REGULATIONS[27]: {
        'regulation_group': 'MLA',
        'published_at': datetime(2019, 2, 7),
        'approved': True,
        'valid_between': DateTimeTZRange(BREXIT, None),
        'information_text': (
            '''The Invasive Non-native Species (Amendment etc.) (EU Exit) Regulations 2019|'''
            '''S.I. 2019/223|https://www.legislation.gov.uk/uksi/2019/223'''
        )
    },
    NEW_REGULATIONS[28]: {
        'regulation_group': 'MLA',
        'published_at': datetime(2018, 11, 13),
        'approved': True,
        'valid_between': DateTimeTZRange(BREXIT, None),
        'information_text': (
            '''The Export of Objects of Cultural Interest (Control) (Amendment etc.) (EU Exit) Regulations 2018|'''
            '''S.I. 2018/1186|https://www.legislation.gov.uk/uksi/2018/1186'''
        )
    },
    NEW_REGULATIONS[29]: {
        'regulation_group': 'MLA',
        'published_at': datetime(2019, 1, 16),
        'approved': True,
        'valid_between': DateTimeTZRange(BREXIT, None),
        'information_text': (
            '''The Control of Mercury (Amendment) (EU Exit) Regulations 2019|'''
            '''S.I. 2019/96|https://www.legislation.gov.uk/uksi/2019/96'''
        )
    },
    NEW_REGULATIONS[30]: {
        'regulation_group': 'MLA',
        'published_at': datetime(2019, 3, 26),
        'approved': True,
        'valid_between': DateTimeTZRange(BREXIT, None),
        'information_text': (
            '''The Organic Production and Control (Amendment) (EU Exit) Regulations 2019|'''
            '''S.I. 2019/693|https://www.legislation.gov.uk/uksi/2019/693'''
        )
    },
    NEW_REGULATIONS[31]: {
        'regulation_group': 'MLA',
        'published_at': datetime(2019, 3, 14),
        'approved': True,
        'valid_between': DateTimeTZRange(BREXIT, None),
        'information_text': (
            '''The International Waste Shipments (Amendment) (EU Exit) Regulations 2019|'''
            '''S.I. 2019/590|https://www.legislation.gov.uk/uksi/2019/590'''
        )
    },
    NEW_REGULATIONS[32]: {
        'regulation_group': 'MLA',
        'published_at': datetime(2013, 2, 6),
        'approved': True,
        'valid_between': DateTimeTZRange(BREXIT, None),
        'information_text': (
            '''The Timber and Timber Products (Placing on the Market) Regulations 2013|'''
            '''S.I. 2013/233|https://www.legislation.gov.uk/uksi/2013/233'''
        )
    },
}
REGULATION_MAPPING_OLD_NEW = {
    'D140284': 'C2100230',
    'R140494': 'A1907820',
    'R200625': 'C2100260',
    'R130743': 'A1907950',
    'R091005': 'X1905830',
    'D070275': 'A1907820',
    'R192007': 'C2100270',
    'R970088': 'C2100310',
    'R201336': 'C2100320',
    'D060232': 'P1900030',
    'D050394': 'P1900040',
    'R050111': 'X1907420',
    'R180273': 'C2100270',
    'R070341': 'C2100240',
    'R080514': 'C2100280',
    'R080555': 'C2100270',
    'R100640': 'A1913120',
    'R080972': 'C2100240',
    'R031210': 'X2007070',
    'R161237': 'A1908120',
    'R131259': 'X1907420',
    'R081295': 'A1914050',
    'R131308': 'A1908220',
    'R061368': 'A1908480',
    'R071375': 'C2100300',
    'R161443': 'X1907420',
    'R031984': 'A1907530',
    'R110284': 'A1906640',
    'R110321': 'C2100290',
    'R110333': 'X1906200',
    'R060972': 'C2100240',
    'R022368': 'X1908440',
    'R913254': 'A1900160',
    'D980238': 'P1900010',
    'R191262': 'A1902230',
    'R150949': 'A1906640',
    'R090116': 'X1811860',
    'R170852': 'X1900960',
    'R070834': 'X1906930',
    'R061013': 'X1905900',
    'D190854': 'X1302330',
}


class NewRow:
    pass


class OGDImportExportControlsImporter(RowsImporter):
    def setup(self) -> Iterator[TrackedModel]:
        if not self.first_run:
            return []
        self.measure_types = {}
        for measure_type in MEASURE_TYPES:
            self.measure_types[measure_type] = MeasureType.objects.get(sid=measure_type)
        self.old_rows = NomenclatureTreeCollector[List[OldMeasureRow]](BREXIT)
        self.brexit_to_infinity = DateTimeTZRange(BREXIT, None)
        self.generating_regulations = {}
        for i, regulation_id in enumerate(NEW_REGULATIONS):
            params = NEW_REGULATION_PARAMS[regulation_id]
            logger.debug(params['regulation_group'])
            params['regulation_group'] = Group.objects.get(group_id=params['regulation_group'])
            generating_regulation, _ = Regulation.objects.get_or_create(
                regulation_id=regulation_id,
                role_type=RoleType.BASE,
                workbasket=self.workbasket,
                update_type=UpdateType.CREATE,
                **params,
            )
            self.generating_regulations[regulation_id] = generating_regulation
            yield generating_regulation

        self.measure_ender = MeasureEndingPattern(
            workbasket=self.workbasket,
            measure_types=self.measure_types,
        )
        self.measure_creator = MeasureCreatingPatternWithExpression(
            duty_sentence_parser=None,
            generating_regulation=None,
            workbasket=self.workbasket,
            measure_sid_counter=self.counters["measure_sid_counter"],
            measure_condition_sid_counter=self.counters[
                "measure_condition_sid_counter"
            ],
        )

    def handle_row(
        self,
        new_row: None,
        old_row: OldMeasureRow,
    ) -> Iterator[List[TrackedModel]]:
        old_regulation_id_trimmed = old_row.regulation_id[:-1]
        replacement_regulation_id = REGULATION_MAPPING_OLD_NEW.get(old_regulation_id_trimmed, None)
        replacement_regulation = self.generating_regulations[replacement_regulation_id] if replacement_regulation_id else None
        transfer = REGULATION_MEASURE_TYPE_TRANSFER[(old_regulation_id_trimmed, old_row.measure_type)]
        if (not transfer and replacement_regulation) or (transfer and not replacement_regulation):
            raise ValueError(
                f'Measure reg:{old_row.regulation_id}/measure_type{old_row.measure_type} '
                f'{"should not " if not transfer else ""}have replacement regulation'
            )
        if transfer is None:
            logger.debug(
                f'This measure should have already been transferred: '
                f'reg:{old_row.regulation_id}/measure_type{old_row.measure_type}'
            )
            return []

        # terminate green/red measures
        yield list(
            self.measure_ender.end_date_measure(
                old_row=old_row,
                terminating_regulation=replacement_regulation
                if transfer else Regulation.objects.get(
                    regulation_id=old_row.regulation_id,
                    role_type=old_row.regulation_role,
                )
                # else (
                #     Regulation.objects.get(
                #         regulation_id='X1904610',
                #         role_type=RoleType.BASE,
                #     )
                #     if (old_regulation_id_trimmed == 'R120267' and old_row.measure_type == '709')
                #     else Regulation.objects.get(
                #         regulation_id=old_row.regulation_id,
                #         role_type=old_row.regulation_role
                #     )
                # )
            )
        )

        # transfer green measures
        if transfer:
            yield from self.make_new_measure(old_row, replacement_regulation)

    def make_new_measure(
        self,
        old_row: OldMeasureRow,
        regulation: Regulation,
    ) -> Iterator[List[TrackedModel]]:
        footnotes = [
            Footnote.objects.as_at(BREXIT).get(
                footnote_id=f[2:], footnote_type__footnote_type_id=f[0:2]
            )
            for f in old_row.footnotes
        ]

        additional_code = None
        if old_row.additional_code_sid:
            additional_code = AdditionalCode.objects.get(
                sid=old_row.additional_code_sid,
            )
        # Parse duty expression
        parsed_duty_expression = parse_duty_parts(old_row.duty_condition_parts, EUR_GBP_CONVERSION_RATE) \
            if old_row.duty_condition_parts else []

        yield list(
            self.measure_creator.create(
                geography=GeographicalArea.objects.as_at(BREXIT).get(
                    sid=old_row.geo_sid,
                ),
                goods_nomenclature=old_row.goods_nomenclature,
                new_measure_type=self.measure_types[old_row.measure_type],
                validity_start=BREXIT,
                footnotes=footnotes,
                duty_condition_expressions=parsed_duty_expression,
                additional_code=additional_code,
                generating_regulation=regulation,
            )
        )


class Command(BaseCommand):
    help = "Imports an OGD import/export control format spreadsheet"

    def add_arguments(self, parser):
        parser.add_argument(
            "old-spreadsheet",
            help="The XLSX file containing existing measures to be parsed.",
            type=str,
        )
        parser.add_argument(
            "--old-skip-rows",
            help="The number of rows from the spreadsheet to skip before importing data",
            type=int,
            default=0,
        )
        parser.add_argument(
            "--measure-sid",
            help="The SID value to use for the first new measure",
            type=int,
            default=200000000,
        )
        parser.add_argument(
            "--measure-condition-sid",
            help="The SID value to use for the first new measure condition",
            type=int,
            default=200000000,
        )
        parser.add_argument(
            "--transaction-id",
            help="The ID value to use for the first transaction",
            type=int,
            default=140,
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
        old_workbook = xlrd.open_workbook(options["old-spreadsheet"])
        old_worksheet = old_workbook.sheet_by_name("Sheet1")
        old_rows = old_worksheet.get_rows()
        for _ in range(options["old_skip_rows"]):
            next(old_rows)
        workbasket, _ = WorkBasket.objects.get_or_create(
            title=f"OGD import and export controls",
            author=author,
            status=WorkflowStatus.PUBLISHED,
        )

        with open(options["output"], mode="wb") as output:
            with EnvelopeSerializer(
                output,
                envelope_id=options["envelope_id"],
                transaction_counter=counter_generator(options["transaction_id"]),
                message_counter=counter_generator(start=1),
                max_envelope_size_in_mb=30,
            ) as env:
                importer = OGDImportExportControlsImporter(
                    workbasket,
                    env,
                )
                importer.counters["measure_sid_counter"] = counter_generator(options["measure_sid"])
                importer.counters[
                    "measure_condition_sid_counter"
                ] = counter_generator(
                    options["measure_condition_sid"]
                )

                old_groups = split_groups(list(old_rows), "B", ["W", "L", "I"])
                logger.debug(old_groups.keys())
                group_ids = OrderedSet(
                    list(old_groups.keys())
                )
                for i, group_by_id in enumerate(group_ids):
                    old_group_rows = old_groups.get(group_by_id, [])
                    logger.debug(str([x[1] for x in old_group_rows]))
                    logger.debug(
                        f"processing group {group_by_id}: {i + 1}/{len(group_ids)} with "
                        f"{len(old_group_rows)} old rows"
                    )
                    importer.import_sheets(
                        (),
                        (OldMeasureRow(row) for row in old_group_rows),
                    )
                    importer.first_run = False
