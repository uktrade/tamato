import pytest
from django.db import IntegrityError
from django.urls import reverse

from common.models.transactions import Transaction
from common.models.utils import override_current_transaction
from common.serializers import AutoCompleteSerializer
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


def test_quota_order_number_get_current_origins():
    """Test that `get_current_origins()` returns the current version of origins
    associated to a quota order number via SID not PK."""
    workbasket = factories.WorkBasketFactory.create()

    old_version = factories.QuotaOrderNumberFactory.create()
    new_version = old_version.new_version(workbasket=workbasket)

    origin1 = factories.QuotaOrderNumberOriginFactory.create(order_number=old_version)
    origin2 = factories.QuotaOrderNumberOriginFactory.create(order_number=new_version)

    with override_current_transaction(Transaction.objects.last()):
        assert origin1 in new_version.get_current_origins()
        assert origin2 in new_version.get_current_origins()


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


def test_quota_order_number_autocomplete_label(date_ranges):
    """Tests that quota order number autocomplete label displays order number
    with validity period."""
    order_number = factories.QuotaOrderNumberFactory.create(
        order_number="123456",
        valid_between=date_ranges.earlier,
    )
    order_number2 = factories.QuotaOrderNumberFactory.create(
        order_number="123456",
        valid_between=date_ranges.no_end,
    )
    assert (
        order_number.autocomplete_label
        == f"{order_number} ({order_number.valid_between.lower} - {order_number.valid_between.upper})"
    )
    assert order_number.autocomplete_label != order_number2.autocomplete_label

    autocomplete = AutoCompleteSerializer()
    autocomplete_label = autocomplete.to_representation(order_number).get("label")
    assert order_number.autocomplete_label == autocomplete_label


@pytest.mark.parametrize(
    "url_name,exp_path",
    [
        ("create", "/quotas/123456789/quota_definitions/create/"),
        ("list", "/quotas/123456789/quota_definitions/"),
        ("confirm-create", "/quota_definitions/987654321/confirm-create/"),
        ("confirm-delete", "/quota_definitions/987654321/confirm-delete/"),
        ("edit", "/quota_definitions/987654321/edit/"),
        ("edit-update", "/quota_definitions/987654321/edit-update/"),
        ("confirm-update", "/quota_definitions/987654321/confirm-update/"),
        ("delete", "/quota_definitions/987654321/delete/"),
    ],
)
def test_quota_definition_urls(url_name, exp_path):
    quota = factories.QuotaOrderNumberFactory.create(sid=123456789)
    definition = factories.QuotaDefinitionFactory.create(
        order_number=quota,
        sid=987654321,
    )
    assert definition.get_url(url_name) == exp_path
