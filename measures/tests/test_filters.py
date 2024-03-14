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


def test_measure_create_process_queue_filters(
    valid_user_client,
):
    # TODO: Tidy this up
    sp = MeasuresBulkCreatorFactory.create(
        processing_state=ProcessingState.SUCCESSFULLY_PROCESSED,
    )
    ap = MeasuresBulkCreatorFactory.create(
        processing_state=ProcessingState.AWAITING_PROCESSING,
    )
    cp = MeasuresBulkCreatorFactory.create(
        processing_state=ProcessingState.CURRENTLY_PROCESSING,
    )
    MeasuresBulkCreatorFactory.create(
        processing_state=ProcessingState.CANCELLED,
    )
    MeasuresBulkCreatorFactory.create(
        processing_state=ProcessingState.FAILED_PROCESSING,
    )
    # TODO: And this
    success_url = f"{reverse('measure-create-process-queue')}?processing_state=SUCCESSFULLY_PROCESSED"
    processing_url = f"{reverse('measure-create-process-queue')}?processing_state=AWAITING_PROCESSING&processing_task=CURRENTLY_PROCESSING"
    failed_url = (
        f"{reverse('measure-create-process-queue')}?processing_state=FAILED_PROCESSED"
    )
    cancelled_url = (
        f"{reverse('measure-create-process-queue')}?processing_state=CANCELLED"
    )
    all_url = f"{reverse('measure-create-process-queue')}?processing_state="
    # TODO: And all of this
    success_response = valid_user_client.get(success_url)
    assert success_response.status_code == 200
    page = BeautifulSoup(
        success_response.content.decode(success_response.charset),
        "html.parser",
    )
    assert page.find("span", class_="tamato-badge-light-green")

    processing_response = valid_user_client.get(processing_url)
    assert processing_response.status_code == 200
    page = BeautifulSoup(
        processing_response.content.decode(processing_response.charset),
        "html.parser",
    )
    res = page.find_all("span", class_="tamato-badge-light-blue")
    assert len(res) == 2

    failed_response = valid_user_client.get(failed_url)
    assert failed_response.status_code == 200
    page = BeautifulSoup(
        failed_response.content.decode(failed_response.charset),
        "html.parser",
    )
    assert page.find("span", class_="tamato-badge-light-red")

    cancelled_response = valid_user_client.get(cancelled_url)
    assert cancelled_response.status_code == 200
    page = BeautifulSoup(
        cancelled_response.content.decode(cancelled_response.charset),
        "html.parser",
    )
    assert page.find("span", class_="tamato-badge-light-yellow")

    all_response = valid_user_client.get(all_url)
    assert all_response.status_code == 200
    page = BeautifulSoup(
        all_response.content.decode(all_response.charset),
        "html.parser",
    )
    assert page.find("span", class_="tamato-badge-light-green")
    assert page.find("span", class_="tamato-badge-light-blue")
    assert page.find("span", class_="tamato-badge-light-red")
    assert page.find("span", class_="tamato-badge-light-yellow")

    assert 0

    # data={"measure_filters_modifier": "current"}
    # queryset = MeasuresBulkCreator.objects.all()
    # filter = MeasureCreateTaskFilter()
    # filter.queryset = queryset
    # filter.filters['processing_state'] is ChoiceFilter
    # filter = MeasureCreateTaskFilter(
    #     queryset,
    #     filters={'processing_state': 'CANCELLED'}
    #     )
    # filter = MeasureCreateTaskFilter(
    #     data={
    #         "queryset": queryset,
    #         "processing_state": 'CANCELLED_PROCESSING'
    #     }
    # )
    # filter.filters = {'processing_state': 'CANCELLED_PROCESSING'}
    # measure_filter = MeasureFilter(
    #     data={"certificates": certificate.trackedmodel_ptr_id},
    # )
