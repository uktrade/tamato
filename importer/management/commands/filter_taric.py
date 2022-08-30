from django.core.management import BaseCommand

from common.xml.util import remove_transactions
from common.xml.util import rewrite


class Command(BaseCommand):
    help = str(remove_transactions.__doc__)

    def add_arguments(self, parser) -> None:
        parser.add_argument("file", type=str, help="The XML file to filter, in place")
        parser.add_argument("name", type=str, help="The XML tag name to look for")
        parser.add_argument(
            "values",
            type=str,
            nargs="*",
            help="String value that the XML tag should have to be removed",
        )
        return super().add_arguments(parser)

    def handle(self, *args, **options):
        with rewrite(options["file"]) as root:
            remove_transactions(root, options["name"], options["values"])
