import pytest

from common.tests import factories
from common.util import TaricDateRange

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


def get_future_date_range(prev_date_range, years):
    lower = prev_date_range.lower.replace(year=prev_date_range.lower.year + years)
    upper = prev_date_range.upper
    if upper:
        upper = prev_date_range.upper.replace(year=prev_date_range.upper.year + years)

    return TaricDateRange(lower, upper)
