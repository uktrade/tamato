import logging
import sys
from datetime import timedelta

import xlrd
from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from psycopg2._range import DateTimeTZRange

from common.renderers import counter_generator
from common.validators import UpdateType
from geo_areas.validators import AreaCode
from importer.management.commands.patterns import BREXIT
from importer.management.commands.patterns import MeasureEndingPattern
from importer.management.commands.patterns import OldMeasureRow
from importer.management.commands.utils import EnvelopeSerializer, create_geo_area, \
    add_geo_area_members, terminate_geo_area_members, update_geo_area_description
from measures.models import MeasurementUnit
from regulations.models import Regulation
from workbaskets.models import WorkBasket
from workbaskets.validators import WorkflowStatus

logger = logging.getLogger(__name__)

BREXIT_TO_INFINITY = DateTimeTZRange(BREXIT, None)
EU_MEMBER_SIDS = [
    36,
    47,
    90,
    91,
    92,
    104,
    106,
    117,
    118,
    122,
    148,
    153,
    169,
    195,
    236,
    256,
    264,
    265,
    266,
    270,
    317,
    340,
    390,
    395,
    397,
    403,
    428,
    430,
]   # 349


class Command(BaseCommand):
    help = "Adjust geo areas"

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
            "--transaction-id",
            help="The ID value to use for the first transaction",
            type=int,
            default=140,
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
            title=f"Terminate EU measures",
            author=author,
            status=WorkflowStatus.PUBLISHED,
        )
        workbasket2, _ = WorkBasket.objects.get_or_create(
            title=f"Adjust geo areas",
            author=author,
            status=WorkflowStatus.PUBLISHED,
        )
        counters = {"group_area_sid_counter": counter_generator(
            options["group_area_sid"]
        ), "group_area_description_sid_counter": counter_generator(
            options["group_area_description_sid"]
        )}

        with open(options["output"], mode="wb") as output:
            with EnvelopeSerializer(
                output,
                envelope_id=options["envelope_id"],
                transaction_counter=counter_generator(options["transaction_id"]),
                message_counter=counter_generator(start=1),
                max_envelope_size_in_mb=30,
            ) as env:
                measure_ender = MeasureEndingPattern(
                    workbasket=workbasket,
                )
                for transaction in self.create_transactions(measure_ender, old_rows):
                    env.render_transaction(transaction)
                for transaction in self.create_geo_area_transactions(workbasket2, counters):
                    for model in transaction:
                        model.save()
                        pass
                    env.render_transaction(transaction)

    def create_transactions(self, measure_ender, old_rows):
        for row in old_rows:
            old_measure_row = OldMeasureRow(row)
            logger.debug(f'Processing regulation: {old_measure_row.regulation_id}')
            yield list(
                measure_ender.end_date_measure(
                    old_row=old_measure_row,
                    terminating_regulation=Regulation.objects.get(
                        regulation_id=old_measure_row.regulation_id,
                        role_type=old_measure_row.regulation_role,
                    )
                )
            )

    def create_geo_area_transactions(self, workbasket, counters):

        # Add new measurement units
        yield [
            MeasurementUnit(
                code="MGM",
                description="Milligram",
                abbreviation="mg",
                valid_between=BREXIT_TO_INFINITY,
                workbasket=workbasket,
                update_type=UpdateType.CREATE,
            )
        ]
        yield [
            MeasurementUnit(
                code="MCG",
                description="Microgram",
                abbreviation="µg",
                valid_between=BREXIT_TO_INFINITY,
                workbasket=workbasket,
                update_type=UpdateType.CREATE,
            )
        ]
        yield [
            MeasurementUnit(
                code="MLT",
                description="Millilitre",
                abbreviation="ml",
                valid_between=BREXIT_TO_INFINITY,
                workbasket=workbasket,
                update_type=UpdateType.CREATE,
            )
        ]
        yield [
            MeasurementUnit(
                code="MCL",
                description="Microlitre",
                abbreviation="μl",
                valid_between=BREXIT_TO_INFINITY,
                workbasket=workbasket,
                update_type=UpdateType.CREATE,
            )
        ]

        # Jersey and Guernsey
        jersey_area_parts = list(create_geo_area(
            valid_between=BREXIT_TO_INFINITY,
            workbasket=workbasket,
            description='Jersey',
            area_id='JE',
            area_sid=counters['group_area_sid_counter'](),
            area_description_sid=counters['group_area_description_sid_counter'](),
            type=AreaCode.REGION,
        ))
        yield jersey_area_parts
        guernsey_area_parts = list(create_geo_area(
            valid_between=BREXIT_TO_INFINITY,
            workbasket=workbasket,
            description='Guernsey',
            area_id='GG',
            area_sid=counters['group_area_sid_counter'](),
            area_description_sid=counters['group_area_description_sid_counter'](),
            type=AreaCode.REGION,
        ))
        yield guernsey_area_parts

        yield list(create_geo_area(
            valid_between=BREXIT_TO_INFINITY,
            workbasket=workbasket,
            description='Areas subject to VAT',
            area_id='1400',
            area_sid=counters['group_area_sid_counter'](),
            area_description_sid=counters['group_area_description_sid_counter'](),
            type=AreaCode.GROUP,
            member_sids=[guernsey_area_parts[0].sid, jersey_area_parts[0].sid],
        ))

        # remove egypt, add Cameroon, Ghana and Moldova from GSP areas
        # yield list(terminate_geo_area_members(
        #     end_date=BREXIT - timedelta(days=1),
        #     workbasket=workbasket,
        #     group_area_sid=217,
        #     member_area_sids=[
        #         109,    # Egypt
        #     ]
        # ))
        yield list(add_geo_area_members(
            valid_between=BREXIT_TO_INFINITY,
            workbasket=workbasket,
            group_area=217,
            member_area_sids=[
                260,    # Cameroon
                211,    # Ghana
                279,    # Moldova
            ],
        ))

        # add eu and members to "All third countries"
        yield list(add_geo_area_members(
            valid_between=BREXIT_TO_INFINITY,
            workbasket=workbasket,
            group_area=68,
            member_area_sids=EU_MEMBER_SIDS,
        ))

        # add eu members to "Member countries of WTO"
        yield list(add_geo_area_members(
            valid_between=BREXIT_TO_INFINITY,
            workbasket=workbasket,
            group_area=215,
            member_area_sids=set(EU_MEMBER_SIDS) - set([169]),
        ))

        # add eu members to "Erga Omnes"
        yield list(add_geo_area_members(
            valid_between=BREXIT_TO_INFINITY,
            workbasket=workbasket,
            group_area=400,
            member_area_sids=set(EU_MEMBER_SIDS) - set([169]),
        ))

        # remove AQ, AW, BL, BQ, CW, GL, NC, PF, PM, SX, TF, WF
        # from OCTs (Overseas Countries and Territories)
        yield list(terminate_geo_area_members(
            end_date=BREXIT - timedelta(days=1),
            workbasket=workbasket,
            group_area_sid=445,
            member_area_sids=[
                138,     # Antarctica
                378,     # Aruba
                456,     # Saint Barthélemy
                458,     # Bonaire, Sint Eustatius and Saba
                459,     # Curaçao
                49,      # Greenland
                342,     # New Caledonia
                197,     # French Polynesia
                427,     # Saint Pierre and Miquelon
                460,     # Sint Maarten (Dutch part)
                370,     # French Southern Territories
                393,     # Wallis and Futuna
            ]
        ))

        # Update West Balkan Countries (AL, BA, ME, MK, XK, XS)
        # 88   # Kosovo *
        # 180  # North Macedonia *
        # 346  # Serbia
        # 348  # Montenegro *
        # 376  # Albania *
        # 431  # Bosnia and Herzegovina
        # to be Kosovo, Albania, North Macedonia, Montenegro
        # and change description to "Western Balkan countries"
        yield list(terminate_geo_area_members(
            end_date=BREXIT - timedelta(days=1),
            workbasket=workbasket,
            group_area_sid=484,
            member_area_sids=[
                346,  # Serbia
                431,  # Bosnia and Herzegovina
            ]
        ))
        yield list(update_geo_area_description(
            valid_between=BREXIT_TO_INFINITY,
            workbasket=workbasket,
            group_area_sid=484,
            old_area_description_sid=1356,
            new_area_description_sid=counters['group_area_description_sid_counter'](),
            description="West Balkan Countries",
        ))

        # Update description to be "UK-Canada agreement: re-imported goods",
        # remove EU membership, add UK membership.
        yield list(terminate_geo_area_members(
            end_date=BREXIT - timedelta(days=1),
            workbasket=workbasket,
            group_area_sid=485,
            member_area_sids=[
                169,  # EU
            ]
        ))
        yield list(add_geo_area_members(
            valid_between=BREXIT_TO_INFINITY,
            workbasket=workbasket,
            group_area=485,
            member_area_sids=[
                331,  # United Kingdom
            ],
        ))
        yield list(update_geo_area_description(
            valid_between=BREXIT_TO_INFINITY,
            workbasket=workbasket,
            group_area_sid=485,
            old_area_description_sid=1359,
            new_area_description_sid=counters['group_area_description_sid_counter'](),
            description="UK-Canada agreement: re-imported goods",
        ))
        # Update description to be "EU-Switzerland agreement: re-imported goods",
        # remove EU membership, add UK membership.
        yield list(terminate_geo_area_members(
            end_date=BREXIT - timedelta(days=1),
            workbasket=workbasket,
            group_area_sid=232,
            member_area_sids=[
                169,  # EU
            ]
        ))
        yield list(add_geo_area_members(
            valid_between=BREXIT_TO_INFINITY,
            workbasket=workbasket,
            group_area=232,
            member_area_sids=[
                331,  # United Kingdom
            ],
        ))
        yield list(update_geo_area_description(
            valid_between=BREXIT_TO_INFINITY,
            workbasket=workbasket,
            group_area_sid=232,
            old_area_description_sid=1099,
            new_area_description_sid=counters['group_area_description_sid_counter'](),
            description="UK-Switzerland agreement: re-imported goods",
        ))

        # Add eu individual member states to steel safeguards
        yield list(add_geo_area_members(
            valid_between=BREXIT_TO_INFINITY,
            workbasket=workbasket,
            group_area=496,
            member_area_sids=set(EU_MEMBER_SIDS) - set([169])
        ))

        # Remove KM, MG from Eastern and Southern Africa States
        yield list(terminate_geo_area_members(
            end_date=BREXIT - timedelta(days=1),
            workbasket=workbasket,
            group_area_sid=455,
            member_area_sids=[
                338,    # Comoros
                341,    # Madagascar
            ]
        ))

