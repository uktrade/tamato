import logging
import sys
from collections import namedtuple
from datetime import datetime
from typing import Iterator
from typing import List
from typing import Optional

import xlrd
from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from psycopg2._range import DateTimeTZRange

from commodities.models import GoodsNomenclature
from common.models import TrackedModel
from common.renderers import counter_generator
from common.validators import UpdateType
from geo_areas.models import GeographicalArea
from importer.management.commands.doc_importer import RowsImporter
from importer.management.commands.patterns import BREXIT, LONDON
from importer.management.commands.patterns import MeasureCreatingPattern
from importer.management.commands.patterns import MeasureEndingPattern
from importer.management.commands.patterns import OldMeasureRow
from importer.management.commands.utils import EnvelopeSerializer, create_geo_area
from importer.management.commands.utils import col
from measures.models import MeasureType, MeasurementUnit
from quotas.models import QuotaDefinition, QuotaOrderNumber, QuotaOrderNumberOrigin, QuotaOrderNumberOriginExclusion, \
    QuotaAssociation
from quotas.validators import AdministrationMechanism, QuotaCategory, SubQuotaType
from regulations.models import Group
from regulations.models import Regulation
from workbaskets.models import WorkBasket
from workbaskets.validators import WorkflowStatus

logger = logging.getLogger(__name__)

PRODUCT_CATEGORY_MAPPING = {
    '1': ['7208100000', '7208250000', '7208260000', '7208270000', '7208360000', '7208370000', '7208380000',
          '7208390000', '7208400000', '7208521000', '7208529900', '7208531000', '7208539000', '7208540000',
          '7211130000', '7211140000', '7211190000', '7212600000', '7225191000', '7225301000', '7225303000',
          '7225309000', '7225401500', '7225409000', '7226191000', '7226912000', '7226919100', '7226919900'],
    '2': ['7209150000', '7209169000', '7209179000', '7209189100', '7209250000', '7209269000', '7209279000',
          '7209289000', '7209902000', '7209908000', '7211232000', '7211233000', '7211238000', '7211290000',
          '7211902000', '7211908000', '7225502000', '7225508000', '7226200000', '7226920000'],
    '4A': ['7210410020', '7210490020', '7210610020', '7210690020', '7212300020', '7212506120', '7212506920',
           '7225920020', '7225990011', '7225990022', '7225990045', '7225990091', '7225990092', '7226993010',
           '7226997011', '7226997091', '7226997094', '7226993030', '7226997013', '7226997093'],
    '4B': ['7210200000', '7210300000', '7210908000', '7212200000', '7212502000', '7212503000', '7212504000',
           '7212509000', '7225910000', '7226991000', '7210410030', '7210410080', '7210490030', '7210490080',
           '7210610030', '7210610080', '7210690030', '7210690080', '7212300080', '7212506130', '7212506180',
           '7212506930', '7212506980', '7225920080', '7225990023', '7225990041', '7225990093', '7225990095',
           '7226993090', '7226997019', '7226997096', '7212300030', '7225920030'],
    '5': ['7210708000', '7212408000'],
    '6': ['7209189900', '7210110000', '7210122000', '7210128000', '7210500000', '7210701000', '7210904000',
          '7212101000', '7212109000', '7212402000'],
    '7': ['7208512000', '7208519100', '7208519800', '7208529100', '7208902000', '7208908000', '7210903000',
          '7225401200', '7225404000', '7225406000'],
    '12': ['7214300000', '7214911000', '7214919000', '7214993100', '7214993900', '7214995000', '7214997100',
           '7214997900', '7214999500', '7215900000', '7216100000', '7216210000', '7216220000', '7216401000',
           '7216409000', '7216501000', '7216509100', '7216509900', '7216990000', '7228102000', '7228201000',
           '7228209100', '7228302000', '7228304100', '7228304900', '7228306100', '7228306900', '7228307000',
           '7228308900', '7228602000', '7228608000', '7228701000', '7228709000', '7228800000'],
    '13': ['7214200000', '7214991000'],
    '14': ['7222111100', '7222111900', '7222118100', '7222118900', '7222191000', '7222199000', '7222201100',
           '7222201900', '7222202100', '7222202900', '7222203100', '7222203900', '7222208100', '7222208900',
           '7222305100', '7222309100', '7222309700', '7222401000', '7222405000', '7222409000'],
    '15': ['7221001000', '7221009000'],
    '16': ['7213100000', '7213200000', '7213911000', '7213912000', '7213914100', '7213914900', '7213917000',
           '7213919000', '7213991000', '7213999000', '7227100000', '7227200000', '7227901000', '7227905000',
           '7227909500'],
    '17': ['7216311000', '7216319000', '7216321100', '7216321900', '7216329100', '7216329900', '7216331000',
           '7216339000'],
    '19': ['7302102200', '7302102800', '7302104000', '7302105000', '7302400000'],
    '20': ['7306304100', '7306304900', '7306307200', '7306307700'],
    '21': ['7306611000', '7306619200', '7306619900'],
    '25A': ['7305110000', '7305120000'],
    '25B': ['7305190000', '7305200000', '7305310000', '7305390000', '7305900000'],
    '26': ['7306111000', '7306119000', '7306191000', '7306199000', '7306210000', '7306290000', '7306301100',
           '7306301900', '7306308000', '7306402000', '7306408000', '7306502000', '7306508000', '7306691000',
           '7306699000', '7306900000'],
    '27': ['7215100000', '7215501100', '7215501900', '7215508000', '7228109000', '7228209900', '7228502000',
           '7228504000', '7228506100', '7228506900', '7228508000'],
    '28': ['7217101000', '7217103100', '7217103900', '7217105000', '7217109000', '7217201000', '7217203000',
           '7217205000', '7217209000', '7217304100', '7217304900', '7217305000', '7217309000', '7217902000',
           '7217905000', '7217909000'],
}

# 5050 group
# What about the ones not listed in 5050?
#  - Stores and provisions within the framework of trade with Third Countries? (244)
#  - Countries and territories not specified within the framework of trade with third countries? (251)
#  - Kosovo (As defined by United Nations Security Council Resolution 1244 of 10 June 1999) (XK) (88)
#  - Bahamas (42)
OTHER_COUNTRIES_GROUP = {
    '5002_group': [
        '31', '32', '33', '34', '35', '40', '42', '45', '49', '57', '58', '59', '67', '85', '86', '88',
        '94', '97', '98', '100', '102', '103', '105', '108', '109', '115', '121', '138', '140', '143',
        '145', '146', '149', '150', '154', '155', '156', '180', '191', '192', '197', '199', '201', '208',
        '214', '219', '244', '247', '249', '251', '255', '258', '267', '269', '273', '276', '279', '282',
        '296', '306', '307', '312', '314', '316', '321', '328', '330', '334', '335', '337', '338', '342',
        '343', '346', '369', '370', '377', '378', '382', '383', '384', '386', '388', '391', '392', '393',
        '405', '406', '422', '424', '425', '427', '431', '433', '434', '437', '439', '440', '443', '456',
        '457', '458', '459', '460', '461', '462',
    ],  # 106 countries from 5002 group
    'extra_from_eu': ['169', '53', '252', '286'],  # EU, Iceland, Norway, Liechtenstein
    'potential_non_dev_exemptions_not_in_5002': ['100', '94', '39'],   # Turkey, Brazil, Saudi Arabia
    'new_dev_exemptions_and_trade_agreements': ['59', '109', '214', '279', '282', '42'],
    # Dev exemptions: Mexico, Egypt, Indonesia, Moldova, Malaysia / Partnerships: Bahamas
}

# 5051 group
LARGE_TRADER_GROUP = {
    'Belarus': '97',
    'China': '439',
    'EU': '169',
    'India': '154',
    'Japan': '156',
    'Norway': '252',
    'Russia': '199',
    'South Korea': '273',
    'Taiwan': '102',
    'Thailand': '98',
    'Turkey': '100',
    'UAE': '312',
    'Ukraine': '388',
    'USA': '103',
}

COUNTRY_SID_MAPPING = {
    'Belarus': '97',
    'Brazil': '94',
    'China': '439',
    'EU': '169',
    'India': '154',
    'Japan': '156',
    'Large Traders': '497',   # new 5051 group
    'Norway': '252',
    'Other Countries': '496',   # new 5050 group
    'Russia': '199',
    'Saudi Arabia': '39',
    'South Korea': '273',
    'Taiwan': '102',
    'Thailand': '98',
    'Third Countries': '68',
    'Turkey': '100',
    'UAE': '312',
    'Ukraine': '388',
    'USA': '103',
    'Vietnam': '392',
}

Q3_END = LONDON.localize(datetime(2021, 3, 31))
Q4_END = LONDON.localize(datetime(2021, 6, 30))

QuotaCap = namedtuple(
    "QuotaCap", "rule cap_volume"
)


class NewRow:
    def __init__(
            self,
            geo_area,
            geo_area_exemptions,
    ) -> None:
        try:
            self.geo_area = GeographicalArea.objects.as_at(BREXIT).get(
                sid=COUNTRY_SID_MAPPING[geo_area]
            )
            self.geo_area_exemptions = [
                GeographicalArea.objects.as_at(BREXIT).get(
                    sid=COUNTRY_SID_MAPPING[exemption]
                ) for exemption in geo_area_exemptions
            ]
        except GeographicalArea.DoesNotExist:
            logger.error(
                "Failed to find geographical area %s", geo_area
            )
            raise


class NonPreferentialTariffRow(NewRow):

    def __init__(
        self,
        geo_area,
        geo_area_exemptions,
        date_range,
        quota,
        order_number,
        large_trader_residual_caps_order_numbers,
        product_category,
        residual_quota_cap,
        initial_quarter=False,
        final_quarter=False,
    ) -> None:
        try:
            super().__init__(geo_area, geo_area_exemptions)
            self.quarter_date_range = self._get_date_range(date_range)
            self.quarter_start_to_infinity = self._get_date_range(date_range, infinity=True)
            self.quota = quota
            self.order_number = order_number
            self.quarter_date_range = self._get_date_range(date_range)
            self.large_trader_sids = [
                COUNTRY_SID_MAPPING[value] for value in large_trader_residual_caps_order_numbers.keys()
            ] if large_trader_residual_caps_order_numbers else None
            self.large_trader_residual_caps_order_numbers = dict(
                (
                    GeographicalArea.objects.as_at(BREXIT).get(
                        sid=COUNTRY_SID_MAPPING[key]
                    ),
                    value
                ) for (key, value) in large_trader_residual_caps_order_numbers.items()
            ) if large_trader_residual_caps_order_numbers else None
            self.is_residual_quota = geo_area == 'Other Countries'
            self.final_quarter = final_quarter
            self.initial_quarter = initial_quarter
            self.product_category = product_category
            self.residual_quota_cap = residual_quota_cap

        except GeographicalArea.DoesNotExist:
            logger.error(
                "Failed to find geographical area %s", geo_area
            )
            raise

    def _get_date_range(self, date_range, infinity=False):
        dates = date_range.split(' to ')
        start_date = LONDON.localize(datetime.strptime(dates[0], '%d/%m/%y'))
        end_date = None if infinity else LONDON.localize(datetime.strptime(dates[1], '%d/%m/%y'))
        range = DateTimeTZRange(
            start_date,
            end_date,
        )
        return range


class AdditionalDutySafeguardRow(NewRow):
    def __init__(
            self,
            item_id,
            geo_area,
            geo_area_exemptions,
    ) -> None:
        super().__init__(geo_area, geo_area_exemptions)
        self.item_id = item_id
        try:
            self.goods_nomenclature = GoodsNomenclature.objects.as_at(BREXIT).get(
                item_id=self.item_id, suffix="80"
            )
        except GoodsNomenclature.DoesNotExist:
            logger.error(
                "Failed to find goods nomenclature %s/%s", self.item_id, "80"
            )
            raise


class SteelSafeguardsImporter(RowsImporter):

    def setup(self) -> Iterator[TrackedModel]:
        if not self.first_run:
            return []
        self.measure_types = {
            122: MeasureType.objects.get(sid="122"),    # Non-preferential tariff quota
            696: MeasureType.objects.get(sid="696"),    # Additional duties (safeguard)
        }
        self.duty_sentences = {
            'quota': '0.00%',
            'additional': '25.00%'
        }
        self.kg_measurement_unit = MeasurementUnit.objects.get(code="KGM")
        self.brexit_to_infinity = DateTimeTZRange(BREXIT, None)
        self.brexit_to_q3_end = DateTimeTZRange(BREXIT, Q3_END)
        self.brexit_to_q4_end = DateTimeTZRange(BREXIT, Q4_END)

        self.generating_regulation_non_preferential_quota, _ = Regulation.objects.get_or_create(
            regulation_id="C2100007",
            regulation_group=Group.objects.get(group_id="KON"),
            published_at=BREXIT,
            approved=False,
            valid_between=self.brexit_to_infinity,
            workbasket=self.workbasket,
            update_type=UpdateType.CREATE,
        )
        yield self.generating_regulation_non_preferential_quota

        self.generating_regulation_additional_duties, _ = Regulation.objects.get_or_create(
            regulation_id="C2100008",
            regulation_group=Group.objects.get(group_id="TXC"),
            published_at=BREXIT,
            approved=False,
            valid_between=self.brexit_to_infinity,
            workbasket=self.workbasket,
            update_type=UpdateType.CREATE,
        )
        yield self.generating_regulation_additional_duties

        yield list(self._create_safeguard_other_countries_group())
        # yield list(self._create_safeguard_larger_trader_group())

        self.measure_ender = MeasureEndingPattern(
            workbasket=self.workbasket,
            measure_types=self.measure_types,
        )
        self.measure_creator_non_preferential_quota = MeasureCreatingPattern(
            generating_regulation=self.generating_regulation_non_preferential_quota,
            workbasket=self.workbasket,
            duty_sentence_parser=self.duty_sentence_parser,
            measure_sid_counter=self.counters["measure_sid_counter"],
            measure_condition_sid_counter=self.counters[
                "measure_condition_sid_counter"
            ],
        )
        self.measure_creator_additional_duties = MeasureCreatingPattern(
            generating_regulation=self.generating_regulation_additional_duties,
            workbasket=self.workbasket,
            duty_sentence_parser=self.duty_sentence_parser,
            measure_sid_counter=self.counters["measure_sid_counter"],
            measure_condition_sid_counter=self.counters[
                "measure_condition_sid_counter"
            ],
        )
        self.quota_order_numbers = {}
        # self.large_traders_geo_area = GeographicalArea.objects.as_at(BREXIT).get(
        #     sid=COUNTRY_SID_MAPPING['Large Traders']
        # )

    def _create_safeguard_larger_trader_group(self):
        yield from create_geo_area(
            self.brexit_to_infinity, self.workbasket,
            area_sid=497,
            area_id='5051',
            area_description_sid=1416,
            description='Countries subject to UK safeguard measures (large traders)',
            member_sids=LARGE_TRADER_GROUP.values(),
        )

    def _create_safeguard_other_countries_group(self):
        member_sids = (
          (
              set(OTHER_COUNTRIES_GROUP['5002_group']) | set(OTHER_COUNTRIES_GROUP['extra_from_eu'])
          ) - set(OTHER_COUNTRIES_GROUP['new_dev_exemptions_and_trade_agreements'])
        ) | set(OTHER_COUNTRIES_GROUP['potential_non_dev_exemptions_not_in_5002'])
        yield from create_geo_area(
            self.brexit_to_infinity, self.workbasket,
            area_sid=496,
            area_id='5050',
            area_description_sid=1415,
            description='Countries subject to UK safeguard measures',
            member_sids=member_sids,
        )

    def handle_row(
        self,
        new_row: Optional[NewRow],
        old_row: Optional[OldMeasureRow],
    ) -> List[TrackedModel]:

        if old_row:
            if old_row.measure_type == '122':
                generating_regulation = self.generating_regulation_non_preferential_quota
            elif old_row.measure_type == '696':
                generating_regulation = self.generating_regulation_additional_duties
            else:
                raise ValueError('Unexpected measure type for old row')
            yield list(
                self.measure_ender.end_date_measure(
                    old_row,
                    generating_regulation,
                )
            )

        if new_row and isinstance(new_row, AdditionalDutySafeguardRow):
            yield list(
                self.measure_creator_additional_duties.create(
                    duty_sentence=self.duty_sentences['additional'],
                    geography=new_row.geo_area,
                    geo_exclusion_list=new_row.geo_area_exemptions,
                    goods_nomenclature=new_row.goods_nomenclature,
                    new_measure_type=self.measure_types[696],
                    authorised_use=False,
                    validity_start=BREXIT,
                )
            )

        elif new_row and isinstance(new_row, NonPreferentialTariffRow):
            if new_row.initial_quarter \
                    or (new_row.final_quarter and new_row.is_residual_quota and new_row.product_category != '25A'):
                if new_row.initial_quarter:
                    valid_between = self.brexit_to_q3_end if \
                        new_row.is_residual_quota and new_row.product_category != '25A' else \
                        self.brexit_to_q4_end
                elif new_row.final_quarter and new_row.is_residual_quota and new_row.product_category != '25A':
                    valid_between = new_row.quarter_date_range

                quota_order_number = self.create_quota_order(
                    valid_between=DateTimeTZRange(
                        valid_between.lower,
                        None
                    ),  # quota order number doesn't need end date
                    order_number=new_row.order_number,
                )
                # keep track of orders to use by later rows
                self.quota_order_numbers[new_row.order_number] = quota_order_number
                quota_origin, quota_exclusions = self.create_quota_origin(
                    quota_order_number=quota_order_number,
                    geo_area=new_row.geo_area,
                    geo_area_exemptions=new_row.geo_area_exemptions,
                )
                yield [quota_order_number, quota_origin] + quota_exclusions

                for item_id in PRODUCT_CATEGORY_MAPPING[new_row.product_category]:
                    logger.debug(
                        f'Processing item {item_id}'
                    )
                    quota_measure_parts = list(self.create_quota_measure(
                        quota_order_number=quota_order_number,
                        valid_between=valid_between,
                        geo_area=new_row.geo_area,
                        geo_area_exemptions=new_row.geo_area_exemptions,
                        goods_nomenclature=GoodsNomenclature.objects.as_at(BREXIT).get(
                            item_id=item_id, suffix="80"
                        ),
                    ))
                    yield quota_measure_parts

            quota_order_number = self.quota_order_numbers[new_row.order_number]
            main_quota_definition = self.create_quota_definition(
                quota_order_number=quota_order_number,
                quota=new_row.quota,
                valid_between=new_row.quarter_date_range,
            )
            yield [main_quota_definition]

            if new_row.final_quarter and \
                    new_row.is_residual_quota and \
                    new_row.large_trader_sids:
                yield from self.create_sub_quotas(
                    product_category=new_row.product_category,
                    main_quota_definition=main_quota_definition,
                    residual_quota_cap=new_row.residual_quota_cap,
                    large_trader_sids=new_row.large_trader_sids,
                    large_trader_residual_caps_order_numbers=new_row.large_trader_residual_caps_order_numbers,
                )

    def create_sub_quotas(
            self,
            product_category,
            main_quota_definition,
            residual_quota_cap,
            large_trader_sids,
            large_trader_residual_caps_order_numbers
    ):
        if residual_quota_cap.rule == '70% Individual':
            # Rule 70% Individual: no exporting country will be allowed to individually
            # use more than 70% of the residual quota
            for large_trader, order_number in large_trader_residual_caps_order_numbers.items():
                sub_quota_order_number = self.create_quota_order(
                    valid_between=DateTimeTZRange(
                        main_quota_definition.valid_between.lower,
                        None
                    ),
                    order_number=order_number,
                )
                sub_quota_origin, _ = self.create_quota_origin(
                    quota_order_number=sub_quota_order_number,
                    geo_area=large_trader,
                )
                yield [sub_quota_order_number, sub_quota_origin]

                sub_quota_definition = self.create_quota_definition(
                    quota_order_number=sub_quota_order_number,
                    quota=residual_quota_cap.cap_volume,
                    valid_between=main_quota_definition.valid_between,
                )
                quota_association = QuotaAssociation(
                    main_quota=main_quota_definition,
                    sub_quota=sub_quota_definition,
                    sub_quota_relation_type=SubQuotaType.NORMAL,
                    update_type=UpdateType.CREATE,
                    workbasket=self.workbasket,
                )
                yield [sub_quota_definition, quota_association]

                for item_id in PRODUCT_CATEGORY_MAPPING[product_category]:
                    yield list(self.create_quota_measure(
                        quota_order_number=sub_quota_order_number,
                        valid_between=main_quota_definition.valid_between,
                        geo_area=large_trader,
                        geo_area_exemptions=None,
                        goods_nomenclature=GoodsNomenclature.objects.as_at(BREXIT).get(
                            item_id=item_id, suffix="80"
                        ),
                    ))

        elif residual_quota_cap.rule == '0':
            # Rule 0: Countries with a country-specific quota will
            # not be allowed to access the residual quota. No sub quota's need to be added
            pass

        elif residual_quota_cap.rule == 'Specific' or residual_quota_cap.rule == '1':
            # Rule Specific: only access to a specific volume of the residual quota
            # will be allowed, proportional to the volume allowed under the existing EU quota
            #
            # Rule 1: No restrictions on access
            # to the residual quota (= specific with 100% volume cap)

            # Order number should be same for all large traders
            order_number = next(iter(large_trader_residual_caps_order_numbers.values()))
            if not all(value == order_number for value in large_trader_residual_caps_order_numbers.values()):
                raise ValueError('Residual cap order number should be same for this cap rule')

            sub_quota_order_number = self.create_quota_order(
                valid_between=DateTimeTZRange(
                    main_quota_definition.valid_between.lower,
                    None
                ),
                order_number=order_number,
            )
            sub_quota_origins = []
            for sid in large_trader_sids:
                sub_quota_origin, _ = self.create_quota_origin(
                    quota_order_number=sub_quota_order_number,
                    geo_area=GeographicalArea.objects.as_at(BREXIT).get(
                        sid=sid
                    ),
                )
                sub_quota_origins.append(sub_quota_origin)

            yield [sub_quota_order_number] + sub_quota_origins

            sub_quota_definition = self.create_quota_definition(
                quota_order_number=sub_quota_order_number,
                quota=residual_quota_cap.cap_volume,
                valid_between=main_quota_definition.valid_between,
            )
            quota_association = QuotaAssociation(
                main_quota=main_quota_definition,
                sub_quota=sub_quota_definition,
                sub_quota_relation_type=SubQuotaType.NORMAL,
                update_type=UpdateType.CREATE,
                workbasket=self.workbasket,
            )
            yield [sub_quota_definition, quota_association]

            for item_id in PRODUCT_CATEGORY_MAPPING[product_category]:
                for sid in large_trader_sids:
                    yield list(self.create_quota_measure(
                        quota_order_number=sub_quota_order_number,
                        valid_between=main_quota_definition.valid_between,
                        geo_area=GeographicalArea.objects.as_at(BREXIT).get(
                            sid=sid
                        ),
                        geo_area_exemptions=[],
                        goods_nomenclature=GoodsNomenclature.objects.as_at(BREXIT).get(
                            item_id=item_id, suffix="80"
                        ),
                    ))
        else:
            raise ValueError(f'Quota cap rule not recognized {residual_quota_cap.rule}')

    def create_quota_order(
            self,
            valid_between,
            order_number,
    ):
        return QuotaOrderNumber(
            sid=self.counters['order_number_sid_counter'](),
            order_number=order_number,
            update_type=UpdateType.CREATE,
            workbasket=self.workbasket,
            mechanism=AdministrationMechanism.FCFS,
            category=QuotaCategory.SAFEGUARD,
            valid_between=valid_between,
        )

    def create_quota_origin(
            self,
            quota_order_number,
            geo_area,
            geo_area_exemptions=[],
    ):
        quota_order_number_origin = QuotaOrderNumberOrigin(
            sid=self.counters['order_number_origin_sid_counter'](),
            order_number=quota_order_number,
            geographical_area=geo_area,
            update_type=UpdateType.CREATE,
            workbasket=self.workbasket,
            valid_between=quota_order_number.valid_between,
        )
        quota_order_number_origin_exclusions = []
        for exemption in geo_area_exemptions:
            quota_order_number_origin_exclusions.append(
                QuotaOrderNumberOriginExclusion(
                    origin=quota_order_number_origin,
                    excluded_geographical_area=exemption,
                    update_type=UpdateType.CREATE,
                    workbasket=self.workbasket,
                )
            )
        return quota_order_number_origin, quota_order_number_origin_exclusions

    def create_quota_measure(
            self,
            quota_order_number,
            valid_between,
            geo_area,
            geo_area_exemptions,
            goods_nomenclature,
    ):
        return self.measure_creator_non_preferential_quota.create(
            duty_sentence=self.duty_sentences['quota'],
            geography=geo_area,
            geo_exclusion_list=geo_area_exemptions,
            goods_nomenclature=goods_nomenclature,
            new_measure_type=self.measure_types[122],
            order_number=quota_order_number,
            authorised_use=False,
            validity_start=valid_between.lower,
            validity_end=valid_between.upper,
        )

    def create_quota_definition(
        self,
        quota_order_number,
        quota,
        valid_between,
    ) -> Iterator[List[TrackedModel]]:
        return QuotaDefinition(
            sid=self.counters['quota_definition_sid_counter'](),
            order_number=quota_order_number,
            initial_volume=quota,
            volume=quota,
            valid_between=valid_between,
            maximum_precision=3,
            quota_critical_threshold=90,
            measurement_unit=self.kg_measurement_unit,
            update_type=UpdateType.CREATE,
            workbasket=self.workbasket,
        )


class Command(BaseCommand):
    help = "Imports a Steel Safeguard format spreadsheet"

    def add_arguments(self, parser):
        parser.add_argument(
            "new-spreadsheet",
            help="The XLSX file to be parsed.",
            type=str,
        )
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
            "--quota-order-number-sid",
            help="The SID value to use for the first new quota order number",
            type=int,
            default=140,
        )
        parser.add_argument(
            "--quota-order-number-origin-sid",
            help="The SID value to use for the first new quota order origin number",
            type=int,
            default=140,
        )
        parser.add_argument(
            "--quota-definition-sid",
            help="The SID value to use for the first quota definition",
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

        new_workbook = xlrd.open_workbook(options["new-spreadsheet"])
        quota_sheet = new_workbook.sheet_by_name("Version 1")
        non_exemption_sheet = new_workbook.sheet_by_name("Non-exemptions")
        residual_caps_sheet = new_workbook.sheet_by_name("Residual Quota Caps Inc EU")

        old_workbook = xlrd.open_workbook(options["old-spreadsheet"])
        old_worksheet = old_workbook.sheet_by_name("Sheet1")

        workbasket, _ = WorkBasket.objects.get_or_create(
            title=f"Steel Safeguards",
            author=author,
            status=WorkflowStatus.PUBLISHED,
        )

        dev_country_exemptions = self._parse_dev_country_exemptions(non_exemption_sheet.get_rows())
        residual_caps = self._parse_residual_caps(residual_caps_sheet.get_rows())

        with open(options["output"], mode="w", encoding="UTF8") as output:
            with EnvelopeSerializer(
                output,
                1,
                counter_generator(options["transaction_id"]),
                counter_generator(start=1),
            ) as env:
                quota_rows = quota_sheet.get_rows()
                old_rows = old_worksheet.get_rows()
                for _ in range(options["old_skip_rows"]):
                    next(old_rows)

                measure_sid_counter = counter_generator(options["measure_sid"])
                measure_condition_sid_counter = counter_generator(
                    options["measure_condition_sid"]
                )
                order_number_sid_counter = counter_generator(
                    options["quota_order_number_sid"]
                )
                order_number_origin_sid_counter = counter_generator(
                    options["quota_order_number_origin_sid"]
                )
                quota_definition_sid_counter = counter_generator(
                    options["quota_definition_sid"]
                )

                importer = SteelSafeguardsImporter(workbasket, env)
                importer.counters["measure_sid_counter"] = measure_sid_counter
                importer.counters[
                    "measure_condition_sid_counter"
                ] = measure_condition_sid_counter
                importer.counters["order_number_sid_counter"] = order_number_sid_counter
                importer.counters["order_number_origin_sid_counter"] = order_number_origin_sid_counter
                importer.counters["quota_definition_sid_counter"] = quota_definition_sid_counter

                # Terminate old Additional Duties
                importer.import_sheets(
                    (),
                    (OldMeasureRow(row) for row in old_rows),
                )
                importer.first_run = False  # Do not regenerate setup transactions on next runs

                # Start new additional duties
                importer.import_sheets(
                   self._generate_additional_duty_safeguard_rows(
                       dev_country_exemptions
                   ),
                   (),
                )

                # Start new non-preferential tariff quota's
                importer.import_sheets(
                   self._generate_non_preferential_quota_rows_from_policy_sheet(
                       quota_rows,
                       dev_country_exemptions,
                       residual_caps
                   ),
                   (),
                )

    def _generate_additional_duty_safeguard_rows(self, dev_country_exemptions):
        for product_category, item_list in PRODUCT_CATEGORY_MAPPING.items():
            for item_id in item_list:
                yield AdditionalDutySafeguardRow(
                    item_id=item_id,
                    geo_area='Other Countries',
                    geo_area_exemptions=dev_country_exemptions[product_category],
                )

    def _generate_non_preferential_quota_rows_from_policy_sheet(
            self,
            rows,
            dev_country_exemptions,
            residual_caps_per_category
    ):

        # first row
        row = next(rows)
        date_range_q3 = row[col("D")].value.strip()
        date_range_q4 = row[col("F")].value.strip()

        # skip two rows
        next(rows)
        next(rows)

        large_traders_for_current_category = []
        large_trader_residual_caps_order_numbers = {}
        for row in rows:
            product_category = row[col("A")].value.strip() or product_category
            residual_cap = residual_caps_per_category[product_category]
            area = row[col("C")].value.strip()
            if area == 'Other Countries':
                # large traders can only use their own quota's
                exemptions = list(set(dev_country_exemptions[product_category] + \
                                      large_traders_for_current_category))
                exemptions.sort()
                #if len(exemptions) != len(set(exemptions)):
                #    raise ValueError(f'No duplicate exemptions allowed: {exemptions}')
            else:   # large trader
                exemptions = []

                # keep track of large traders and their caps order numbers while iterating within category
                large_traders_for_current_category.append(area)
                residual_cap_order_number = row[col("H")].value.strip()
                if residual_cap_order_number != '':
                    large_trader_residual_caps_order_numbers[area] = residual_cap_order_number

            logger.debug(
                f'Processing category {product_category}/ area {area} \n'
                f' - exemptions {exemptions} \n'
                f' - residual cap {residual_cap} \n'
                f' - large traders {large_traders_for_current_category}'
            )
            # third quarter
            yield NonPreferentialTariffRow(
                geo_area=area,
                geo_area_exemptions=exemptions,
                date_range=date_range_q3,
                quota=int(row[col("E")].value) * 1000,    # convert tonne to kg
                order_number=row[col("D")].value.strip(),
                product_category=product_category,
                large_trader_residual_caps_order_numbers=None,    # only required for residual quota in Q4
                residual_quota_cap=None,   # only required for residual quota in Q4
                initial_quarter=True,
            )
            # fourth quarter
            yield NonPreferentialTariffRow(
                geo_area=area,
                geo_area_exemptions=exemptions,
                date_range=date_range_q4,
                quota=int(row[col("G")].value) * 1000,    # convert tonne to kg
                order_number=row[col("F")].value.strip(),
                product_category=product_category,
                large_trader_residual_caps_order_numbers=large_trader_residual_caps_order_numbers,
                residual_quota_cap=residual_cap,
                final_quarter=True,
            )
            if area == 'Other Countries':
                # Reset values when starting new category
                large_traders_for_current_category = []
                large_trader_residual_caps_order_numbers = {}

    def _parse_dev_country_exemptions(self, rows):

        def _get_cell_values(row, start, end):
            return [row[i].value.strip() for i in range(start, end+1)]

        # skip three rows
        for _ in range(3):
            next(rows)

        country_list = _get_cell_values(next(rows), 2, 10)
        exemptions_per_category = {}
        for row in rows:
            category = row[0].value.strip()
            crosses = _get_cell_values(row, 2, 10)
            country_exemptions = [
                country for i, country in enumerate(country_list) if crosses[i] != 'X'
            ]
            if category != '4':
                exemptions_per_category[category] = country_exemptions
            else:
                exemptions_per_category['4A'] = country_exemptions
                exemptions_per_category['4B'] = country_exemptions
        return exemptions_per_category

    def _parse_residual_caps(self, rows):

        # skip three rows
        for _ in range(3):
            next(rows)

        residual_cap_per_category = {}
        for row in rows:
            category = row[0].value.strip()
            if category == '':
                break
            rule = row[1].value.strip()
            cap_volume = row[3].value
            if cap_volume in ['N/A', '-']:
                cap_volume = None
            else:
                cap_volume = int(cap_volume) * 1000   # convert to kg
            residual_cap_per_category[category] = QuotaCap(rule=rule, cap_volume=cap_volume)
        return residual_cap_per_category
