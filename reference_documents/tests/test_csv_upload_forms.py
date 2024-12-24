from datetime import date
from decimal import Decimal

import pytest
from django.urls import reverse

from reference_documents.tests import factories

pytestmark = pytest.mark.django_db

@pytest.mark.reference_documents
class TestReferenceDocumentCreateCsvUploadForm:
    pass