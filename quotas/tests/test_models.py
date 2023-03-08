import pytest
from django.db import IntegrityError
from django.urls import reverse

from common.tests import factories
from common.tests.util import raises_if

pytestmark = pytest.mark.django_db


def test_quota_order_number_in_use(in_use_check_respects_deletes):
    assert in_use_check_respects_deletes(
        factories.QuotaOrderNumberFactory,
        "in_use",
        factories.MeasureFactory,
        "order_number",
    )


def test_quota_order_number_origin_in_use(in_use_check_respects_deletes):
    assert in_use_check_respects_deletes(
        factories.QuotaOrderNumberOriginFactory,
        "order_number_in_use",
        factories.MeasureFactory,
        "order_number",
        through="order_number",
    )


@pytest.mark.parametrize(
    "factory",
    [
        factories.QuotaOrderNumberFactory,
        factories.QuotaOrderNumberOriginFactory,
        factories.QuotaOrderNumberOriginExclusionFactory,
        factories.QuotaDefinitionFactory,
        factories.QuotaAssociationFactory,
        factories.QuotaSuspensionFactory,
        factories.QuotaBlockingFactory,
        factories.QuotaEventFactory,
    ],
)
def test_quota_update_types(
    factory,
    check_update_validation,
):
    assert check_update_validation(
        factory,
    )


def test_required_certificates_persist_across_versions():
    cert = factories.CertificateFactory.create()
    quota = factories.QuotaOrderNumberFactory.create(required_certificates=[cert])
    assert quota.required_certificates.get() == cert

    new_version = quota.new_version(quota.transaction.workbasket)
    assert new_version.required_certificates.get() == cert


def test_required_certificates_changed_if_specified():
    cert = factories.CertificateFactory.create()
    quota = factories.QuotaOrderNumberFactory.create(required_certificates=[cert])
    assert quota.required_certificates.get() == cert

    new_version = quota.new_version(
        quota.transaction.workbasket,
        required_certificates=[],
    )
    assert quota.required_certificates.get() == cert
    assert not new_version.required_certificates.exists()

    third_version = new_version.new_version(
        new_version.transaction.workbasket,
        required_certificates=[cert],
    )
    assert quota.required_certificates.get() == cert
    assert not new_version.required_certificates.exists()
    assert third_version.required_certificates.get() == cert


@pytest.mark.parametrize(
    ("has_unit", "has_currency", "error_expected"),
    (
        (True, True, True),
        (True, False, False),
        (False, True, False),
        (False, False, True),
    ),
)
def test_quota_definition_must_have_one_unit(has_unit, has_currency, error_expected):
    with raises_if(IntegrityError, error_expected):
        factories.QuotaDefinitionFactory.create(
            is_monetary=has_currency,
            is_physical=has_unit,
        )


def test_quota_definition_get_url():
    order_number = factories.QuotaOrderNumberFactory.create()
    definition = factories.QuotaDefinitionFactory.create(order_number=order_number)

    assert (
        definition.get_url()
        == f"{reverse('quota-ui-detail', kwargs={'sid': order_number.sid})}#definition-details"
    )
