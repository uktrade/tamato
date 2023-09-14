import pytest

from common.tests import factories
from measures.filters import MeasureFilter
from measures.models import Measure
from workbaskets.models import WorkBasket

pytestmark = pytest.mark.django_db


def test_filter_by_current_workbasket(
    valid_user_client,
    session_workbasket: WorkBasket,
    session_request,
):
    with session_workbasket.new_transaction() as transaction:
        measure_in_workbasket_1 = factories.MeasureFactory.create(
            transaction=transaction,
        )
        measure_in_workbasket_2 = factories.MeasureFactory.create(
            transaction=transaction,
        )

    factories.MeasureFactory.create()
    factories.MeasureFactory.create()
    session = valid_user_client.session
    session["workbasket"] = {"id": session_workbasket.pk}
    session.save()
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
    assert len(result) == len(session_workbasket.measures)
    assert set(session_workbasket.measures) == set(result)


def test_filter_by_certificates(
    valid_user_client,
    session_workbasket: WorkBasket,
    session_request,
):
    session = valid_user_client.session
    session["workbasket"] = {"id": session_workbasket.pk}
    session.save()

    measure_with_certificate = factories.MeasureFactory.create()
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

    qs = Measure.objects.all()

    self = MeasureFilter(data={"certificates": certificate.trackedmodel_ptr_id})
    res = MeasureFilter.certificates_filter(
        self,
        queryset=qs,
        name="certificates",
        value=certificate,
    )

    assert measure_with_certificate in res
    assert measure_no_certificate not in res
    assert measure_with_different_certificate not in res
