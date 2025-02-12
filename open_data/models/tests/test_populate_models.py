import pytest

from common.models import TrackedModel
from common.tests import factories
from footnotes.models import Footnote
from footnotes.models import FootnoteDescription
from measures.models import Measure
from open_data.models import ReportFootnote
from open_data.models import ReportMeasure
from open_data.models.utils import ReportModel
from open_data.tasks import populate_open_data

pytestmark = pytest.mark.django_db

excluded_models = [
    "QuotaEvent",  # excluded because not available in sqlite exported to data.gov
    "GeographicalAreaDescription",  # Description are merged in the described table
    "GoodsNomenclatureIndent",
    "GoodsNomenclatureDescription",
    "AdditionalCodeDescription",
    "FootnoteAssociationAdditionalCode",
    "CertificateDescription",
    "FootnoteDescription",
    "Extension",  # excluded because not available in sqlite exported to data.gov
    "Termination",  # excluded because not available in sqlite exported to data.gov
]

# The following tracked models are created only for testing
test_models = ["TestModel1", "TestModel2", "TestModel3", "TestModelDescription1"]


def test_models_are_included():
    # This test will fail when a new tracked model has been created,
    # without creating an equivalent model in the open data app
    # If the new model is not relevant to open data, its name should be added
    # to excluded_models
    tracked_models = [cls.__name__ for cls in TrackedModel.__subclasses__()]
    report_models = (
        [cls.shadowed_model.__name__ for cls in ReportModel.__subclasses__()]
        + excluded_models
        + test_models
    )
    missing_models = [el for el in tracked_models if el not in report_models]
    if len(missing_models):
        print(missing_models)
    assert len(missing_models) == 0


def test_measures_unpublished_and_unapproved():
    factories.MeasureFactory.create(
        transaction=factories.UnapprovedTransactionFactory.create(),
    )
    factories.MeasureFactory.create(
        transaction=factories.ApprovedTransactionFactory.create(),
    )
    factories.MeasureFactory.create(
        transaction=factories.PublishedTransactionFactory.create(),
    )

    assert Measure.objects.count() == 3
    assert ReportMeasure.objects.count() == 0
    assert Measure.objects.published().count() == 1
    populate_open_data()
    assert Measure.objects.count() == 3
    assert ReportMeasure.objects.count() == 1
    assert Measure.objects.published().count() == 1


def test_footnotes():
    published_transaction = factories.PublishedTransactionFactory.create()
    factories.ApprovedTransactionFactory.create()
    test_description = "Test description"
    assert Footnote.objects.count() == 0
    test_footnote_id = "001"
    factories.FootnoteFactory(
        footnote_id=test_footnote_id,
        transaction=published_transaction,
        description__description=test_description,
    )
    assert Footnote.objects.count() == 1
    assert FootnoteDescription.objects.count() == 1
    # Open data is empty
    assert ReportFootnote.objects.count() == 0
    assert Footnote.objects.published().count() == 1
    populate_open_data()

    # Nothing created or deleted in the footnotes
    assert Footnote.objects.count() == 1
    assert Footnote.objects.published().count() == 1
    assert FootnoteDescription.objects.count() == 1
    # Open data has a record
    assert ReportFootnote.objects.count() == 1
    # and the description is correct
    assert (
        ReportFootnote.objects.get(footnote_id=test_footnote_id).description
        == test_description
    )
