# Exclusions were missing from first TR import script
# This script adds the exclusions to the affected rows

import logging
import sys

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from psycopg2._range import DateTimeTZRange

from common.renderers import counter_generator
from common.validators import UpdateType
from geo_areas.models import GeographicalArea
from importer.management.commands.patterns import BREXIT
from importer.management.commands.utils import EnvelopeSerializer, add_geo_area_members, terminate_geo_area_members
from measures.models import Measure, MeasureExcludedGeographicalArea
from quotas.models import QuotaOrderNumberOrigin, QuotaOrderNumberOriginExclusion, QuotaOrderNumber
from workbaskets.models import WorkBasket
from workbaskets.validators import WorkflowStatus

logger = logging.getLogger(__name__)

BREXIT_TO_INFINITY = DateTimeTZRange(BREXIT, None)


TR_EXCLUSIONS = {
    '20041036': 'Canada, United States',
    '20041059': 'Argentina, Canada, Indonesia, United States',
    '20041037': 'Canada, United States',
    '20041060': 'Argentina, Canada, Indonesia, United States',
    '20041061': 'Argentina, Canada, Indonesia, United States',
    '20041038': 'Canada, United States',
    '20041039': 'Canada, United States',
    '20041062': 'Argentina, Canada, Indonesia, United States',
    '20041040': 'Canada, United States',
    '20041063': 'Argentina, Canada, Indonesia, United States',
    '20041041': 'Canada, United States',
    '20041064': 'Argentina, Canada, Indonesia, United States',
    '20041042': 'Canada, United States',
    '20041065': 'Argentina, Canada, Indonesia, United States',
    '20041066': 'Argentina, Canada, Indonesia, United States',
    '20041043': 'Canada, United States',
    '20041044': 'Canada, United States',
    '20041067': 'Argentina, Canada, Indonesia, United States',
    '20041045': 'Canada, United States',
    '20041068': 'Argentina, Canada, Indonesia, United States',
    '20041069': 'Argentina, Canada, Indonesia, United States',
    '20041046': 'Canada, United States',
    '20041070': 'Argentina, Canada, Indonesia, United States',
    '20041047': 'Canada, United States',
    '20041071': 'Argentina, Canada, Indonesia, United States',
    '20041048': 'Canada, United States',
    '20041049': 'China, Morocco',
    '20041050': 'China, South Korea',
    '20041051': 'China, Morocco',
    '20041052': 'China, South Korea',
    '20041053': 'China, Morocco',
    '20041054': 'China, South Korea',
    '20041055': 'China, Morocco',
    '20041056': 'China, South Korea',
    '20041057': 'China, Morocco',
    '20041058': 'China, South Korea',
}

SID_MAPPING = {
    'Canada': '146',
    'United States': '103',
    'Argentina': '37',
    'Indonesia': '214',
    'China': '439',
    'Morocco': '159',
    'South Korea': '273',
}


class Command(BaseCommand):
    help = "Adjust geo areas"

    def add_arguments(self, parser):
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
        workbasket, _ = WorkBasket.objects.get_or_create(
            title=f"Adjust geo areas",
            author=author,
            status=WorkflowStatus.PUBLISHED,
        )

        with open(options["output"], mode="wb") as output:
            with EnvelopeSerializer(
                output,
                envelope_id=options["envelope_id"],
                transaction_counter=counter_generator(options["transaction_id"]),
                message_counter=counter_generator(start=1030),
                max_envelope_size_in_mb=30,
            ) as env:
                for transaction in self.create_transactions(workbasket):
                    # for model in transaction:
                    #     model.save()
                    #     pass
                    env.render_transaction(transaction)

    def create_transactions(self, workbasket):

        def create_measure_exclusion(
                measure_sid,
                area_sid,
                workbasket,
        ):
            measure = Measure(
                sid=measure_sid
            )
            return MeasureExcludedGeographicalArea(
                modified_measure=measure,
                excluded_geographical_area=GeographicalArea.objects.get(
                    sid=area_sid,
                ),
                update_type=UpdateType.CREATE,
                workbasket=workbasket,
            )

        for measure_sid, exclusions in TR_EXCLUSIONS.items():
            tr_exclusions = []
            for member in exclusions.split(", "):
                tr_exclusions.append(create_measure_exclusion(
                    measure_sid=measure_sid,
                    area_sid=SID_MAPPING[member],
                    workbasket=workbasket,
                ))
            yield tr_exclusions

