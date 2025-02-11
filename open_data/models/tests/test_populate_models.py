import pytest

from common.models import TrackedModel
from common.tests import factories
from measures.models import Measure
from open_data.models import ReportMeasure
from open_data.models.utils import ReportModel
from open_data.tasks import update_all_tables

pytestmark = pytest.mark.django_db

excluded_list = [
    "QuotaEvent",
    "GeographicalAreaDescription",
    "GoodsNomenclatureIndent",
    "GoodsNomenclatureDescription",
    "AdditionalCodeDescription",
    "FootnoteAssociationAdditionalCode",
    "CertificateDescription",
    "FootnoteDescription",
    "Extension",
    "Termination",
]


def test_models_are_included():
    tracked_model_list = [cls.__name__ for cls in TrackedModel.__subclasses__()]
    report_model_list = [
        cls.shadowed_model.__name__ for cls in ReportModel.__subclasses__()
    ] + excluded_list
    [el for el in tracked_model_list if el not in report_model_list]


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
    update_all_tables()
    assert Measure.objects.count() == 3
    assert ReportMeasure.objects.count() == 1
    assert Measure.objects.published().count() == 1


def test_footnotes():
    approved_transaction = factories.ApprovedTransactionFactory.create()
    test_description = "Test description"
    foot = factories.FootnoteFactory(
        transaction=approved_transaction,
        description=factories.FootnoteDescriptionFactory(
            transaction=approved_transaction,
            description=test_description,
        ),
        footnote_type=factories.FootnoteTypeFactory(transaction=approved_transaction),
    )
    assert Measure.objects.count() == 3
    assert ReportMeasure.objects.count() == 0
    assert Measure.objects.published().count() == 1
    update_all_tables()
    assert Measure.objects.count() == 3
    assert ReportMeasure.objects.count() == 1
    assert Measure.objects.published().count() == 1


def footnote_NC000(date_ranges, approved_transaction):
    footnote = factories.FootnoteFactory.create(
        footnote_id="000",
        footnote_type=factories.FootnoteTypeFactory.create(
            footnote_type_id="NC",
            valid_between=date_ranges.no_end,
            transaction=approved_transaction,
        ),
        valid_between=date_ranges.normal,
        transaction=approved_transaction,
        description__description="This is NC000",
        description__validity_start=date_ranges.starts_with_normal.lower,
    )
    factories.FootnoteDescriptionFactory.create(
        described_footnote=footnote,
        validity_start=date_ranges.ends_with_normal.lower,
        transaction=approved_transaction,
    )
    return footnote
