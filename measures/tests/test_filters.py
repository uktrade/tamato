from datetime import date

import pytest
from bs4 import BeautifulSoup
from django.urls import reverse

from common.tests import factories
from common.util import TaricDateRange
from common.validators import UpdateType
from measures.filters import MeasureFilter
from measures.models import Measure
from measures.models.bulk_processing import ProcessingState
from measures.tests.factories import MeasuresBulkCreatorFactory

pytestmark = pytest.mark.django_db


def test_filter_by_current_workbasket(
    valid_user_client,
    user_workbasket,
    session_request,
):
    with user_workbasket.new_transaction() as transaction:
        measure_in_workbasket_1 = factories.MeasureFactory.create(
            transaction=transaction,
        )
        measure_in_workbasket_2 = factories.MeasureFactory.create(
            transaction=transaction,
        )

    factories.MeasureFactory.create()
    factories.MeasureFactory.create()
    self = MeasureFilter(
        data={"measure_filters_modifier": "current"},
        request=session_request,
    )
    qs = Measure.objects.all()
    result = MeasureFilter.measures_filter(
        self,
        queryset=qs,
        name="measure_filters_modifier",
        value="current",
    )
    assert len(result) == len(user_workbasket.measures)
    assert set(user_workbasket.measures) == set(result)


def test_filter_by_certificates(
    valid_user_client,
    user_workbasket,
    session_request,
):
    old_date_range = TaricDateRange(date(2021, 1, 1), date(2023, 1, 1))
    new_date_range = TaricDateRange(date(2023, 1, 1))

    measure_with_certificate = factories.MeasureFactory.create(
        valid_between=old_date_range,
        stopped=True,
    )
    measure_with_different_certificate = factories.MeasureFactory.create()
    measure_no_certificate = factories.MeasureFactory.create()
    certificate = factories.CertificateFactory.create()
    other_certificate = factories.CertificateFactory.create()

    factories.MeasureConditionFactory.create(
        dependent_measure=measure_with_certificate,
        required_certificate=certificate,
    )
    factories.MeasureConditionFactory.create(
        dependent_measure=measure_with_different_certificate,
        required_certificate=other_certificate,
    )

    # update a measure, both updated and original measure_with_certificate should show in result
    new_transaction = factories.TransactionFactory.create()
    updated_measure = measure_with_certificate.new_version(
        workbasket=new_transaction.workbasket,
        transaction=new_transaction,
        update_type=UpdateType.UPDATE,
        valid_between=new_date_range,
        stopped=False,
    )
    factories.MeasureConditionFactory.create(
        dependent_measure=updated_measure,
        required_certificate=certificate,
    )
    qs = Measure.objects.all()

    measure_filter = MeasureFilter(
        data={"certificates": certificate.trackedmodel_ptr_id},
    )
    filtered_measures = measure_filter.certificates_filter(
        queryset=qs,
        name="certificates",
        value=certificate,
    )

    assert measure_with_certificate in filtered_measures
    assert measure_no_certificate not in filtered_measures
    assert measure_with_different_certificate not in filtered_measures
    assert updated_measure in filtered_measures


@pytest.mark.parametrize(
    "query_string, css_class",
    [
        ("SUCCESSFULLY_PROCESSED", "tamato-badge-light-green"),
        ("CANCELLED", "tamato-badge-light-yellow"),
        ("FAILED_PROCESSING", "tamato-badge-light-red"),
    ],
)
def test_measure_create_process_queue_filters(
    query_string,
    css_class,
    valid_user_client,
):
    MeasuresBulkCreatorFactory.create(
        processing_state=ProcessingState.SUCCESSFULLY_PROCESSED,
    )
    MeasuresBulkCreatorFactory.create(
        processing_state=ProcessingState.AWAITING_PROCESSING,
    )
    MeasuresBulkCreatorFactory.create(
        processing_state=ProcessingState.CURRENTLY_PROCESSING,
    )
    MeasuresBulkCreatorFactory.create(
        processing_state=ProcessingState.CANCELLED,
    )
    MeasuresBulkCreatorFactory.create(
        processing_state=ProcessingState.FAILED_PROCESSING,
    )
    url = f"{reverse('measure-create-process-queue')}?processing_state={query_string}"
    response = valid_user_client.get(url)
    assert response.status_code == 200
    page = BeautifulSoup(
        response.content.decode(response.charset),
        "html.parser",
    )
    assert page.find("span", class_=css_class)
    assert not page.find("span", class_="tamato-badge-light-blue")


def test_measure_create_process_queue_filters_processing(
    valid_user_client,
):
    MeasuresBulkCreatorFactory.create(
        processing_state=ProcessingState.SUCCESSFULLY_PROCESSED,
    )
    MeasuresBulkCreatorFactory.create(
        processing_state=ProcessingState.AWAITING_PROCESSING,
    )
    MeasuresBulkCreatorFactory.create(
        processing_state=ProcessingState.CURRENTLY_PROCESSING,
    )
    MeasuresBulkCreatorFactory.create(
        processing_state=ProcessingState.CANCELLED,
    )
    MeasuresBulkCreatorFactory.create(
        processing_state=ProcessingState.FAILED_PROCESSING,
    )
    url = f"{reverse('measure-create-process-queue')}?processing_state=PROCESSING"
    response = valid_user_client.get(url)
    assert response.status_code == 200
    page = BeautifulSoup(
        response.content.decode(response.charset),
        "html.parser",
    )
    assert len(page.find_all("span", class_="tamato-badge-light-blue")) == 2
    assert not page.find("span", class_="tamato-badge-light-green")
    assert not page.find("span", class_="tamato-badge-light-red")
    assert not page.find("span", class_="tamato-badge-light-yellow")
