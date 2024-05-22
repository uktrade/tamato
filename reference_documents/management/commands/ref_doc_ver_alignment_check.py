import os
from datetime import date

import pandas as pd
from django.core.management import BaseCommand

from common.util import TaricDateRange
from reference_documents.check.check_runner import Checks
from reference_documents.models import PreferentialQuota
from reference_documents.models import PreferentialQuotaOrderNumber
from reference_documents.models import PreferentialRate
from reference_documents.models import ReferenceDocument
from reference_documents.models import ReferenceDocumentVersion
from reference_documents.models import ReferenceDocumentVersionStatus


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
        self.reference_document_version = ReferenceDocumentVersion.objects.get(id=self.reference_document_version_id)

        Checks.run(self.reference_document_version)
