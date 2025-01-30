from django.core.management import BaseCommand

from reference_documents.check.check_runner import Checks
from reference_documents.models import ReferenceDocumentVersion


class Command(BaseCommand):
    help = "Run alignment checks against a reference document version"

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "reference_document_version_id",
            type=int,
            help="The id of the reference document version to be checked",
        )

        return super().add_arguments(parser)

    def handle(self, *args, **options):
        self.reference_document_version_id = options["reference_document_version_id"]
        self.reference_document_version = ReferenceDocumentVersion.objects.get(
            id=self.reference_document_version_id,
        )

        Checks.run(self.reference_document_version)
