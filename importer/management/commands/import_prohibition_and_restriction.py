import logging
import sys
from typing import Iterator
from typing import List

import xlrd
from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils.datastructures import OrderedSet
from psycopg2._range import DateTimeTZRange

from common.models import TrackedModel
from common.renderers import counter_generator
from common.validators import UpdateType
from footnotes.models import Footnote, FootnoteType, FootnoteDescription
from footnotes.validators import ApplicationCode
from geo_areas.models import GeographicalArea
from importer.management.commands.doc_importer import RowsImporter
from importer.management.commands.patterns import BREXIT, MeasureCreatingPatternWithExpression
from importer.management.commands.patterns import MeasureEndingPattern
from importer.management.commands.patterns import OldMeasureRow
from importer.management.commands.utils import EnvelopeSerializer, create_geo_area
from importer.management.commands.utils import parse_trade_remedies_duty_expression
from importer.management.commands.utils import split_groups
from measures.models import MeasureType, MeasureTypeSeries
from regulations.models import Group
from regulations.models import Regulation
from workbaskets.models import WorkBasket
from workbaskets.validators import WorkflowStatus

logger = logging.getLogger(__name__)

BREXIT_TO_INFINITY = DateTimeTZRange(BREXIT, None)
MEASURE_MAPPING_OLD_NEW = {
    'AHC': '350',
    'AIL': '351',
    'ATT': '352',
    'CEX': '353',
    'COE': '354',
    'COI': '355',
    'CVD': '356',
    'EQC': '357',
    'HOP': '358',
    'HSE': '359',
    'PHC': '360',
    'PRE': '361',
    'PRT': '362',
    'QRC': '363'
}
REGULATION_MAPPING_OLD_NEW = {
    'Z1970AHC': 'C2100009',
    'Z1970PHC': 'C2100010',
    'Z1970EQC': 'C2100011',
    'Z1970COI': 'C2100012',
    'Z1970ATT': 'C2100013',
    'Z1970PRT': 'C2100014',
    'Z1970COE': 'C2100015',
    'Z1970PRE': 'C2100016',
    'Z1970AIL': 'C2100017',
    'Z1970HSE': 'C2100018',
    'Z1970HOP': 'C2100019',
    'IYY99990': 'C2100020',
    'Z1970QRC': 'C2100021',
    'Z1970CEX': 'C2100022',
}
# SELECT
# 	m.geographical_area_sid
# FROM geographical_area_memberships m
#   LEFT JOIN geographical_areas g
# ON m.geographical_area_sid = g.geographical_area_sid
# WHERE m.geographical_area_group_sid = '-306'
#   and (m.validity_end_date is null or m.validity_end_date >= '2021-01-01'::date)
#   and (g.validity_end_date is null or g.validity_end_date >= '2021-01-01'::date)
# ORDER BY m.geographical_area_sid
GEO_AREA_MAPPING_MEMBERS_GROUP_SID_MEMBER_SID = {
    '-248': ['46', '100', '141', '205', '319', '322', '326'],
    '-298': [
        '39', '46', '59', '94', '100', '101', '141', '149', '154', '162', '199',
        '202', '205', '214', '219', '253', '263', '275', '276', '279', '282', '319',
        '322', '326', '341', '387', '396', '426', '429', '438', '442', '444',
    ],
    '-299': [
        '39', '46', '59', '94', '100', '101', '103', '141', '149', '154', '162', '199',
        '202', '205', '214', '219', '253', '263', '275', '276', '279', '282', '319', '322',
        '326', '341', '387', '396', '426', '429', '438', '442', '444',
    ],
    '-300': [
        '37', '39', '44', '46', '59', '89', '94', '100', '101', '109', '141', '149',
        '152', '154', '162', '199', '202', '205', '219', '253', '263', '268', '275', '276',
        '279', '282', '313', '319', '322', '324', '326', '341', '387', '396', '426', '429',
        '438', '444',
    ],
    '-306': [
        '32', '33', '34', '35', '37', '38', '39', '40', '41', '42', '44', '45', '46', '48', '49', '50', '53', '54',
        '59', '76', '85', '86', '88', '89', '93', '94', '95', '96', '97', '98', '99', '100', '101', '102', '103', '105',
        '107', '108', '109', '111', '112', '113', '115', '116', '119', '120', '121', '122', '138', '140', '141', '142',
        '143', '144', '145', '146', '149', '150', '152', '154', '155', '156', '157', '159', '191', '192', '196', '199',
        '200', '201', '202', '203', '204', '205', '206', '207', '208', '209', '210', '211', '213', '214', '219', '221',
        '222', '223', '247', '252', '253', '254', '255', '257', '258', '259', '260', '261', '262', '263', '267', '268',
        '269', '272', '273', '274', '275', '276', '277', '278', '279', '280', '281', '282', '283', '284', '286', '295',
        '296', '306', '307', '311', '313', '314', '315', '316', '318', '319', '320', '321', '322', '324', '325', '326',
        '327', '328', '330', '333', '334', '336', '337', '338', '339', '342', '343', '346', '348', '369', '370', '374',
        '375', '376', '377', '378', '379', '380', '381', '382', '383', '384', '385', '386', '387', '388', '389', '391',
        '392', '393', '394', '395', '396', '402', '405', '406', '424', '425', '426', '427', '429', '431', '432', '433',
        '434', '435', '436', '437', '438', '439', '440', '441', '442', '443', '444', '446', '448',
    ],
}
GEO_AREA_GROUP_ID_AND_DESCRIPTIONS = {
    '-248': ['6010', 'Home Office - Precursor Drugs Licensing - Exports'],
    '-298': ['6063', 'Home Office - Precursor Drugs Licensing - Exports'],
    '-299': ['6064', 'Home Office - Precursor Drugs Licensing - Exports'],
    '-300': ['6065', 'Home Office - Precursor Drugs Licensing - Exports'],
    '-306': ['6006', 'Phytosanitary certificates'],
}
NEW_FOOTNOTE_TYPES = [
    'PR003',
    'PR009',
    'PR018',
    'PR005',
    'PR004',
    'PR010',
    'PR015',
    'PR016',
    'PR001',
    'PR008',
    'PR007',
    'PR011',
    'PR017',
]
FOOTNOTE_MAPPING_OLD_NEW = {
    '04003': 'PR003',
    '04009': 'PR009',
    '04018': 'PR018',
    '04005': 'PR005',
    '04004': 'PR004',
    '04010': 'PR010',
    '04015': 'PR015',
    '04016': 'PR016',
    '04001': 'PR001',
    '04008': 'PR008',
    '04007': 'PR007',
    '04011': 'PR011',
    '04017': 'PR017',
}
FOOTNOTE_DESCRIPTIONS = {
    '04003': """Contact Details for lead Government Department are as follows: <P> <P>Rabies & Hares - Animal Health Certificate Animal - Rabies Pathogens, Hares <P> <P>Animal Health & Veterinary Laboratories Agency</P><P>Hadrian House</P><P>Wavell Drive</P><P>Rosehill</P><P>Carlisle</P><P>CA1 2TB</P><P>Telephone: 01228 403600</P><P>Fax: 01228 591900</P><P> <P>Animal Pathogens Import Licence <P> <P>The Pathogens Licensing Team <P>Defra <P>Area 5A, Nobel House <P>17 Smith Square,London <P>SW1P 3JR <P>Telephone: 020 7238 6211/6195 <P>Fax: 020 7238 6105 <P>Email:pathogens<sub>d</sub>efra.gsi.gov.uk <P>Website: <a href="http://www.defra.gov.uk/animal-diseases/pathogens/">www.defra.gov.uk/animal-diseases/pathogens/</a>""",
    '04009': """Contact Details for lead Government Department are as follows: <P> <P>Plant and Plant products  <P>Plant Health and Seeds Inspectorate <P>Defra <P>Foss House , <P>Kings Pool <P>1-2 Peasholme Green <P>York . <P>YO1 7PX <P>Telephone: 01904 455174    <P>Email: planthealth.info<sub>d</sub>efra.gsi.gov.uk""",
    '04018': """Contact Details for lead Government Department are as follows: <P>Fruit and Vegetables conformity controls </P> <P>Horticultural Marketing Inspectorate ( HMI) </P><P>Rural Payments Agency </P><P> Office SCF3 South Core Produce Hall </P><P> Western International Market </P><P>Hayes Road </P><P>Southall</P><P>UB2 5XJ </P><P>Telephone 0845 6073224 </P><P>Email: Peachenquiries<sub>r</sub>pa.gsi.gov.uk""",
    '04005': """Contact Details for lead Government Department are as follows: <P>Fruit and Vegetables conformity controls </P> <P>Horticultural Marketing Inspectorate ( HMI) </P><P>Rural Payments Agency </P><P> Office SCF3 South Core Produce Hall </P><P> Western International Market </P><P>Hayes Road </P><P>Southall</P><P>UB2 5XJ </P><P>Telephone 0845 6073224 </P><P>Email: Peachenquiries<sub>r</sub>pa.gsi.gov.uk""",
    '04004': """Where the free rate of duty has been applied due to inclusion of 'Multi-component integrated circuits' (MCOs) document code Y035 (no status or reference required) must be declared at item level in box 44.""",
    '04010': """Contact Details for lead Government Department are as follows: <P> <P>Controlled Drugs Individual & Open Individual Import Licence <P> <P>Home Office <P>Drugs Licensing <P>Peel Building <P>2 Marsham St <P>London SW1P 4DF <P>Telephone: 0207 035 0479/0484 <P> <P>http://drugs.homeoffice.gov.uk/drugs-laws/licensing/import-export/ <P> <P>Note: Applications for import licences must be made online for controlled drugs.""",
    '04015': """Contact Details for lead Government Department are as follows: <P> <P>Controlled Drugs Individual & Open Individual Export Licence <P> <P>Home Office <P>Drugs Licensing <P>Peel Building <P>2 Marsham St <P>London SW1P 4DF <P>Telephone: 0207 035 0476/0484 <P> <P>http://drugs.homeoffice.gov.uk/drugs-laws/licensing/import-export/ <P> <P>Note: Applications for export licences must be made online for controlled drugs.""",
    '04016': """Contact Details for lead Government Department are as follows: <P> <P>Drugs Precursor Chemical Individual Export Licence <P> <P>Home Office <P>Drugs Licensing <P>Peel Building <P>2 Marsham St <P>London SW1P 4DF <P>Tel: 0207 035 0480 <P> <P>Website:http://drugs.homeoffice.gov.uk/drugs-laws/licensing/precursor-forms <P> <P>Note: Applications for export licences cannot be made online for drugs precursor chemicals.""",
    '04001': """<p>Health and Safety Executive</p><p>Import Licensing</p><p>For further information concerning import prohibitions and restrictions for this commodity, please contact:</p><p>Health and Safety Executive</p><p>Mines, Quarries &amp; Explosives Policy</p><p>Rose Court</p><p>2 Southwark Bridge</p><p>London</p><p>SE1 9HS</p><p></p><p>Tel: 0207 717 6205</p><p>Fax: 0207 717 6690</p><p><a href='https://www.gov.uk/import-controls'>www.gov.uk/import-controls</a></p>""",
    '04008': """Contact Details for Explosives Competent Authority Document or Intra Community Transfer document: <P> <P>Health and Safety Executive, <P>Mines, Quarries and Explosives Policy, <P>Rose Court, <P>2 Southwark Bridge, <P>London <P>SE1 9HF <P>Telephone: 0207 717 6262  or 6377 <P> <P>HSE, HM Explosives Inspectorate, Redgrave Court, <P>Merton Road, <P>Bootle, <P>Merseyside <P>L20 7HS <P>Telephone:  0151 951 4025 or 3133""",
    '04007': """Contact Details for lead Government Department are as follows: <P> <P>Home Office Drugs Licensing <P>Peel Building <P>2 Marsham St <P>London <P>SW1P 4DF <P>Telephone: 0207 035 0480 <P>Website: <a href="http://www.homeoffice.gov.uk/drugs/licensing/precursors-chemical-licensing/">www.homeoffice.gov.uk/drugs/licensing/precursors-chemical-licensing</a><P> <P>Note: Applications for import licences cannot be made online for drugs precursor chemicals.""",
    '04011': """Contact Details for lead Government Department are as follows: <P> <P>Forestry  and Wood Products <P>Forestry Commission <P>231 Corstorphine Road <P>Edinburgh <P>EH12 7AT <P>Tel no : 0131 334 0303 <P>enquiries<sub>f</sub>orestry.gsi.gov.uk""",
    '04017': """Contact Details for lead Government Department are as follows: <P><P>Export Licensing Unit <P>Museums, Libraries & Archives Council (MLA) <P>Wellcome Wolfson Building <P>165 Queen's Gate <P>London <P>SW7 5HD <P>Tel: 0207 273 8265 / 8266 / 8267 / 8269 / 8273 <P><P>elu<sub>m</sub>la.gov.uk""",
}

class PnRImporter(RowsImporter):
    def setup(self) -> Iterator[TrackedModel]:
        if not self.first_run:
            return []
        self.brexit_to_infinity = DateTimeTZRange(BREXIT, None)
        self.old_measure_types = {}
        self.new_measure_types = {}
        for old_measure_type_sid, new_measure_type_sid in MEASURE_MAPPING_OLD_NEW.items():
            old_measure_type = MeasureType.objects.get(sid=old_measure_type_sid)
            self.old_measure_types[old_measure_type_sid] = old_measure_type
            new_measure_type = MeasureType(
                sid=new_measure_type_sid,
                trade_movement_code=old_measure_type.trade_movement_code,
                priority_code=old_measure_type.priority_code,
                measure_component_applicability_code=old_measure_type.measure_component_applicability_code,
                origin_destination_code=old_measure_type.origin_destination_code,
                order_number_capture_code=old_measure_type.order_number_capture_code,
                measure_explosion_level=old_measure_type.measure_explosion_level,
                description=old_measure_type.description,
                measure_type_series=MeasureTypeSeries.objects.get(
                    sid='B',
                ),
                valid_between=self.brexit_to_infinity,
                workbasket=self.workbasket,
                update_type=UpdateType.CREATE,
            )
            self.new_measure_types[new_measure_type_sid] = new_measure_type

            # Creating new measure type
            logger.debug(old_measure_type.description)
            yield new_measure_type

        self.generating_regulations = {}
        for old_regulation_id, new_regulation_id in REGULATION_MAPPING_OLD_NEW.items():
            generating_regulation, _ = Regulation.objects.get_or_create(
                regulation_id=new_regulation_id,
                regulation_group=Group.objects.get(group_id="UKR"),
                published_at=BREXIT,
                approved=False,
                valid_between=self.brexit_to_infinity,
                workbasket=self.workbasket,
                update_type=UpdateType.CREATE,
            )
            self.generating_regulations[old_regulation_id] = generating_regulation
            yield generating_regulation

        old_footnote_type = FootnoteType.objects.get(
            footnote_type_id='04',
        )
        new_footnote_type = FootnoteType(
            footnote_type_id='PR',
            application_code=ApplicationCode.OTHER_MEASURES,
            description=old_footnote_type.description,
            valid_between=self.brexit_to_infinity,
            workbasket=self.workbasket,
            update_type=UpdateType.CREATE,
        )
        yield new_footnote_type

        self.new_footnotes = {}
        for new_footnote_id in NEW_FOOTNOTE_TYPES:
            old_footnote = Footnote.objects.get(
                footnote_type=old_footnote_type,
                footnote_id=new_footnote_id[2:],
            )
            new_footnote = Footnote(
                footnote_type=new_footnote_type,
                footnote_id=new_footnote_id[2:],
                valid_between=self.brexit_to_infinity,
                workbasket=self.workbasket,
                update_type=UpdateType.CREATE,
            )
            new_footnote_description = FootnoteDescription(
                description_period_sid=self.counters["footnote_description"](),
                described_footnote=new_footnote,
                description=FOOTNOTE_DESCRIPTIONS['04' + new_footnote_id[2:]],
                valid_between=self.brexit_to_infinity,
                workbasket=self.workbasket,
                update_type=UpdateType.CREATE,
            )
            self.new_footnotes[new_footnote_id] = new_footnote
            yield list([new_footnote, new_footnote_description])

        self.new_geo_areas = {}
        for group_sid, member_sids in GEO_AREA_MAPPING_MEMBERS_GROUP_SID_MEMBER_SID.items():
            group_area_components = list(
                create_geo_area(
                    valid_between=self.brexit_to_infinity,
                    workbasket=self.workbasket,
                    area_sid=self.counters["group_area_sid_counter"](),
                    area_id=GEO_AREA_GROUP_ID_AND_DESCRIPTIONS[group_sid][0],
                    area_description_sid=self.counters["group_area_description_sid_counter"](),
                    description=GEO_AREA_GROUP_ID_AND_DESCRIPTIONS[group_sid][1],
                    member_sids=member_sids,
                )
            )
            self.new_geo_areas[group_sid] = group_area_components[0]
            yield group_area_components

        self.measure_ender = MeasureEndingPattern(
            workbasket=self.workbasket,
            measure_types=self.old_measure_types,
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
        generating_regulation = self.generating_regulations[old_row.regulation_id]
        # yield list(
        #     self.measure_ender.end_date_measure(
        #         old_row,
        #         generating_regulation,
        #     )
        # )
        yield from self.make_new_measure(old_row)

    def make_new_measure(
        self,
        old_row: OldMeasureRow,
    ) -> Iterator[List[TrackedModel]]:
        footnotes = [
            self.new_footnotes[FOOTNOTE_MAPPING_OLD_NEW[f]]
            for f in old_row.footnotes
        ]
        new_measure_type = self.new_measure_types[MEASURE_MAPPING_OLD_NEW[old_row.measure_type]]
        parsed_measure_expressions = parse_trade_remedies_duty_expression(
            old_row.conditions
        )
        # use new mapped area if exists else use existing area
        geo_area = self.new_geo_areas.get(
            str(old_row.geo_sid),
            GeographicalArea.objects.as_at(BREXIT).get(
                 sid=old_row.geo_sid,
            )
        )
        yield list(
            self.measure_creator.create(
                geography=geo_area,
                goods_nomenclature=old_row.goods_nomenclature,
                new_measure_type=new_measure_type,
                validity_start=BREXIT,
                footnotes=footnotes,
                duty_condition_expressions=parsed_measure_expressions,
                additional_code=old_row.additional_code,
                generating_regulation=self.generating_regulations[old_row.regulation_id]
            )
        )


class Command(BaseCommand):
    help = "Imports an import control format spreadsheet"

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
            title=f"Prohibition and restriction",
            author=author,
            status=WorkflowStatus.PUBLISHED,
        )

        with open(options["output"], mode="wb") as output:
            with EnvelopeSerializer(
                output,
                envelope_id=options["envelope_id"],
                transaction_counter=counter_generator(options["transaction_id"]),
                message_counter=counter_generator(start=1),
                max_envelope_size_in_mb=40,
            ) as env:
                importer = PnRImporter(
                    workbasket,
                    env,
                )
                importer.counters["measure_sid_counter"] = counter_generator(options["measure_sid"])
                importer.counters[
                    "measure_condition_sid_counter"
                ] = counter_generator(
                    options["measure_condition_sid"]
                )

                importer.counters[
                    "group_area_sid_counter"
                ] = counter_generator(
                    options["group_area_sid"]
                )
                importer.counters[
                    "group_area_description_sid_counter"
                ] = counter_generator(
                    options["group_area_description_sid"]
                )
                importer.counters[
                    "footnote_description"
                ] = counter_generator(
                    options["footnote_description_sid"]
                )

                # Split by additional code, origin code, measure_type groups
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
