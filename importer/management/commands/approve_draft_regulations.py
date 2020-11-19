import logging
import sys
from datetime import datetime

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from psycopg2._range import DateTimeTZRange

from common.renderers import counter_generator
from common.validators import UpdateType
from importer.management.commands.patterns import BREXIT
from importer.management.commands.utils import EnvelopeSerializer
from regulations.models import Group
from regulations.models import Regulation
from regulations.validators import RoleType
from workbaskets.models import WorkBasket
from workbaskets.validators import WorkflowStatus

logger = logging.getLogger(__name__)

BREXIT_TO_INFINITY = DateTimeTZRange(BREXIT, None)
NEW_REGULATIONS = [
    'C2100001',
    'C2100002',
    'C2100003',
    'C2100004',
    'C2100005',
    'C2100006',
    'C2100007',
    'C2100008',
    'C2100009',
    'C2100010',
    'C2100011',
    'C2100012',
    'C2100013',
    'C2100014',
    'C2100015',
    'C2100016',
    'C2100017',
    'C2100018',
    'C2100019',
    'C2100020',
    'C2100021',
    'C2100022',
    'C2100110',
    'C2100230',
    'C2100240',
    'C2100250',
    'C2100260',
    'C2100270',
    'C2100280',
    'C2100290',
    'C2100300',
    'C2100310',
    'C2100320',
    'C2100330',
]
NEW_REGULATION_PARAMS = {
    NEW_REGULATIONS[0]: {
        'regulation_group': 'DNC',
        'published_at': datetime(2021, 1, 1),
        'approved': False,
        'valid_between': DateTimeTZRange(BREXIT, None),
        'information_text': None
    },
    NEW_REGULATIONS[1]: {
        'regulation_group': 'SPG',
        'published_at': datetime(2021, 1, 1),
        'approved': False,
        'valid_between': DateTimeTZRange(BREXIT, None),
        'information_text': None
    },
    NEW_REGULATIONS[2]: {
        'regulation_group': 'SUS',
        'published_at': datetime(2021, 1, 1),
        'approved': False,
        'valid_between': DateTimeTZRange(BREXIT, None),
        'information_text': None
    },
    NEW_REGULATIONS[3]: {
        'regulation_group': 'TXC',
        'published_at': datetime(2021, 1, 1),
        'approved': False,
        'valid_between': DateTimeTZRange(BREXIT, None),
        'information_text': None
    },
    NEW_REGULATIONS[4]: {
        'regulation_group': 'DUM',
        'published_at': datetime(2021, 1, 1),
        'approved': False,
        'valid_between': DateTimeTZRange(BREXIT, None),
        'information_text': None
    },
    NEW_REGULATIONS[5]: {
        'regulation_group': 'FTA',
        'published_at': datetime(2021, 1, 1),
        'approved': False,
        'valid_between': DateTimeTZRange(BREXIT, None),
        'information_text': None
    },
    NEW_REGULATIONS[6]: {
        'regulation_group': 'KON',
        'published_at': datetime(2021, 1, 1),
        'approved': False,
        'valid_between': DateTimeTZRange(BREXIT, None),
        'information_text': None
    },
    NEW_REGULATIONS[7]: {
        'regulation_group': 'TXC',
        'published_at': datetime(2021, 1, 1),
        'approved': False,
        'valid_between': DateTimeTZRange(BREXIT, None),
        'information_text': None
    },
    NEW_REGULATIONS[8]: {
        'regulation_group': 'UKR',
        'published_at': datetime(2021, 1, 1),
        'approved': False,
        'valid_between': DateTimeTZRange(BREXIT, None),
        'information_text': None
    },
    NEW_REGULATIONS[9]: {
        'regulation_group': 'UKR',
        'published_at': datetime(2021, 1, 1),
        'approved': False,
        'valid_between': DateTimeTZRange(BREXIT, None),
        'information_text': None
    },
    NEW_REGULATIONS[10]: {
        'regulation_group': 'UKR',
        'published_at': datetime(2021, 1, 1),
        'approved': False,
        'valid_between': DateTimeTZRange(BREXIT, None),
        'information_text': None
    },
    NEW_REGULATIONS[11]: {
        'regulation_group': 'UKR',
        'published_at': datetime(2021, 1, 1),
        'approved': False,
        'valid_between': DateTimeTZRange(BREXIT, None),
        'information_text': None
    },
    NEW_REGULATIONS[12]: {
        'regulation_group': 'UKR',
        'published_at': datetime(2021, 1, 1),
        'approved': False,
        'valid_between': DateTimeTZRange(BREXIT, None),
        'information_text': None
    },
    NEW_REGULATIONS[13]: {
        'regulation_group': 'UKR',
        'published_at': datetime(2021, 1, 1),
        'approved': False,
        'valid_between': DateTimeTZRange(BREXIT, None),
        'information_text': None
    },
    NEW_REGULATIONS[14]: {
        'regulation_group': 'UKR',
        'published_at': datetime(2021, 1, 1),
        'approved': False,
        'valid_between': DateTimeTZRange(BREXIT, None),
        'information_text': None
    },
    NEW_REGULATIONS[15]: {
        'regulation_group': 'UKR',
        'published_at': datetime(2021, 1, 1),
        'approved': False,
        'valid_between': DateTimeTZRange(BREXIT, None),
        'information_text': None
    },
    NEW_REGULATIONS[16]: {
        'regulation_group': 'UKR',
        'published_at': datetime(2021, 1, 1),
        'approved': False,
        'valid_between': DateTimeTZRange(BREXIT, None),
        'information_text': None
    },
    NEW_REGULATIONS[17]: {
        'regulation_group': 'UKR',
        'published_at': datetime(2021, 1, 1),
        'approved': False,
        'valid_between': DateTimeTZRange(BREXIT, None),
        'information_text': None
    },
    NEW_REGULATIONS[18]: {
        'regulation_group': 'UKR',
        'published_at': datetime(2021, 1, 1),
        'approved': False,
        'valid_between': DateTimeTZRange(BREXIT, None),
        'information_text': None
    },
    NEW_REGULATIONS[19]: {
        'regulation_group': 'UKR',
        'published_at': datetime(2021, 1, 1),
        'approved': False,
        'valid_between': DateTimeTZRange(BREXIT, None),
        'information_text': None
    },
    NEW_REGULATIONS[20]: {
        'regulation_group': 'UKR',
        'published_at': datetime(2021, 1, 1),
        'approved': False,
        'valid_between': DateTimeTZRange(BREXIT, None),
        'information_text': None
    },
    NEW_REGULATIONS[21]: {
        'regulation_group': 'UKR',
        'published_at': datetime(2021, 1, 1),
        'approved': False,
        'valid_between': DateTimeTZRange(BREXIT, None),
        'information_text': None
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
        'published_at': datetime(2021, 1, 1),
        'approved': False,
        'valid_between': DateTimeTZRange(BREXIT, None),
        'information_text': None
    },
    NEW_REGULATIONS[24]: {
        'regulation_group': 'PRF',
        'published_at': datetime(2021, 1, 1),
        'approved': False,
        'valid_between': DateTimeTZRange(BREXIT, None),
        'information_text': None
    },
    NEW_REGULATIONS[25]: {
        'regulation_group': 'MLA',
        'published_at': datetime(2021, 1, 1),
        'approved': False,
        'valid_between': DateTimeTZRange(BREXIT, None),
        'information_text': None
    },
    NEW_REGULATIONS[26]: {
        'regulation_group': 'PRS',
        'published_at': datetime(2021, 1, 1),
        'approved': False,
        'valid_between': DateTimeTZRange(BREXIT, None),
        'information_text': None
    },
    NEW_REGULATIONS[27]: {
        'regulation_group': 'MLA',
        'published_at': datetime(2021, 1, 1),
        'approved': False,
        'valid_between': DateTimeTZRange(BREXIT, None),
        'information_text': None
    },
    NEW_REGULATIONS[28]: {
        'regulation_group': 'MLA',
        'published_at': datetime(2021, 1, 1),
        'approved': False,
        'valid_between': DateTimeTZRange(BREXIT, None),
        'information_text': None
    },
    NEW_REGULATIONS[29]: {
        'regulation_group': 'MLA',
        'published_at': datetime(2021, 1, 1),
        'approved': False,
        'valid_between': DateTimeTZRange(BREXIT, None),
        'information_text': None
    },
    NEW_REGULATIONS[30]: {
        'regulation_group': 'MLA',
        'published_at': datetime(2021, 1, 1),
        'approved': False,
        'valid_between': DateTimeTZRange(BREXIT, None),
        'information_text': None
    },
    NEW_REGULATIONS[31]: {
        'regulation_group': 'DUM',
        'published_at': datetime(2021, 1, 1),
        'approved': False,
        'valid_between': DateTimeTZRange(BREXIT, None),
        'information_text': None
    },
    NEW_REGULATIONS[32]: {
        'regulation_group': 'DUM',
        'published_at': datetime(2021, 1, 1),
        'approved': False,
        'valid_between': DateTimeTZRange(BREXIT, None),
        'information_text': None
    },
    NEW_REGULATIONS[33]: {
        'regulation_group': 'SUS',
        'published_at': datetime(2021, 1, 1),
        'approved': False,
        'valid_between': DateTimeTZRange(BREXIT, None),
        'information_text': None
    },
}


class Command(BaseCommand):
    help = "Approve draft regulations"

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
            title=f"Approve regulations",
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
                for transaction in self.create_transactions(workbasket):
                    for model in transaction:
                        model.save()
                    env.render_transaction(transaction)

    def create_transactions(self, workbasket):
        for i, regulation_id in enumerate(NEW_REGULATIONS):
            if regulation_id in ['C2100250', 'C2100330']:
                continue
            logger.debug(f'Processing regulation: {regulation_id}')
            params = NEW_REGULATION_PARAMS[regulation_id]
            params['regulation_group'] = Group.objects.get(group_id=params['regulation_group'])
            generating_regulation, _ = Regulation.objects.get_or_create(
                regulation_id=regulation_id,
                role_type=RoleType.BASE,
                workbasket=workbasket,
                update_type=UpdateType.UPDATE,
                **params,
            )
            generating_regulation.approved = True
            yield [generating_regulation]


