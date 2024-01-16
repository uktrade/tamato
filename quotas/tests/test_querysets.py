import pytest

from common.models.utils import override_current_transaction
from common.tests import factories
from quotas import models

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    ("number_of_certificates, is_origin_quota"),
    ((0, False), (1, True)),
)
def test_with_is_origin_quota(number_of_certificates, is_origin_quota: bool):
    """
    Adds a number of required certificates to a QuotaOrderNumberFactory.

    After creating an instance of the model, checks whether it is marked as an
    origin quota.
    """

    model_factory = factories.QuotaOrderNumberFactory.create(
        required_certificates=[
            factories.CertificateFactory.create()
            for _ in range(0, number_of_certificates)
        ],
    )

    test_instance = model_factory._meta.model.objects.with_is_origin_quota().get()
    assert test_instance.origin_quota == is_origin_quota


@pytest.mark.parametrize(
    "model,factory,field",
    [
        (
            models.QuotaOrderNumberOrigin,
            factories.QuotaOrderNumberOriginFactory,
            "geographical_area",
        ),
        (
            models.QuotaOrderNumberOriginExclusion,
            factories.QuotaOrderNumberOriginExclusionFactory,
            "excluded_geographical_area",
        ),
    ],
)
def test_with_latest_geo_area_description_multiple_version(model, factory, field):
    """Tests that, after updating a geo area description,
    with_current_geo_area_description returns a queryset annotated with only the
    latest description."""
    description = factories.GeographicalAreaDescriptionFactory.create(
        description="blarghhh",
    )
    current_description = description.new_version(
        description.transaction.workbasket,
        description="more recent blarghhh",
    )
    params = {field: description.described_geographicalarea}
    factory.create(**params)
    with override_current_transaction(current_description.transaction):
        qs = model.objects.current().with_latest_geo_area_description()

        assert qs.count() == 1
        assert qs.first().geo_area_description == "more recent blarghhh"


@pytest.mark.parametrize(
    "model,factory,field",
    [
        (
            models.QuotaOrderNumberOrigin,
            factories.QuotaOrderNumberOriginFactory,
            "geographical_area",
        ),
        (
            models.QuotaOrderNumberOriginExclusion,
            factories.QuotaOrderNumberOriginExclusionFactory,
            "excluded_geographical_area",
        ),
    ],
)
def test_with_latest_geo_area_description_multiple_descriptions(
    model,
    factory,
    field,
    date_ranges,
):
    """Tests that, where multiple current descriptions exist for an area, the
    description with the latest validity_start date is returned by
    with_latest_description."""
    earlier_description = factories.GeographicalAreaDescriptionFactory.create(
        validity_start=date_ranges.earlier.lower,
    )
    later_description = factories.GeographicalAreaDescriptionFactory.create(
        described_geographicalarea=earlier_description.described_geographicalarea,
        validity_start=date_ranges.later.lower,
    )
    params = {field: later_description.described_geographicalarea}
    factory.create(transaction=later_description.transaction, **params)
    with override_current_transaction(later_description.transaction):
        qs = model.objects.current().with_latest_geo_area_description()

        # sanity check that description objects have been created with different description values
        assert earlier_description.description != later_description.description
        assert qs.first().geo_area_description == later_description.description
