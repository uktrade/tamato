from django.core.management import BaseCommand

from common.xml.util import renumber_transactions
from common.xml.util import rewrite


class Command(BaseCommand):
    help = str(renumber_transactions.__doc__)

    def add_arguments(self, parser) -> None:
        parser.add_argument("file", type=str, help="The XML file to renumber, in place")
        parser.add_argument("number", type=int, help="The number to start from")
        return super().add_arguments(parser)

    def handle(self, *args, **options):
        with rewrite(options["file"]) as root:
            renumber_transactions(root, options["number"])
