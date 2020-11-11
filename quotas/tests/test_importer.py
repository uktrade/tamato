import pytest

from common.tests import factories
from quotas import serializers

pytestmark = pytest.mark.django_db


def test_quota_order_number_importer_create(imported_fields_match):
    assert imported_fields_match(
        factories.QuotaOrderNumberFactory, serializers.QuotaOrderNumberSerializer
    )


def test_quota_order_number_importer_update(update_imported_fields_match):
    assert update_imported_fields_match(
        factories.QuotaOrderNumberFactory, serializers.QuotaOrderNumberSerializer
    )


def test_quota_order_number_origin_importer_create(imported_fields_match):
    assert imported_fields_match(
        factories.QuotaOrderNumberOriginFactory.build(
            order_number=factories.QuotaOrderNumberFactory.create(),
            geographical_area=factories.GeographicalAreaFactory.create(),
        ),
        serializers.QuotaOrderNumberOriginSerializer,
    )


def test_quota_order_number_origin_importer_update(update_imported_fields_match):
    assert update_imported_fields_match(
        factories.QuotaOrderNumberOriginFactory,
        serializers.QuotaOrderNumberOriginSerializer,
        dependencies={
            "order_number": factories.QuotaOrderNumberFactory,
            "geographical_area": factories.GeographicalAreaFactory,
        },
    )


def test_quota_order_number_origin_exclusion_importer_create(imported_fields_match):
    assert imported_fields_match(
        factories.QuotaOrderNumberOriginExclusionFactory.build(
            origin=factories.QuotaOrderNumberOriginFactory.create(),
            excluded_geographical_area=factories.GeographicalAreaFactory.create(),
        ),
        serializers.QuotaOrderNumberOriginExclusionSerializer,
    )


def test_quota_order_number_origin_exclusion_importer_update(
    update_imported_fields_match,
):
    assert update_imported_fields_match(
        factories.QuotaOrderNumberOriginExclusionFactory,
        serializers.QuotaOrderNumberOriginExclusionSerializer,
        dependencies={
            "origin": factories.QuotaOrderNumberOriginFactory,
            "excluded_geographical_area": factories.GeographicalAreaFactory,
        },
        validity=False,
    )


def test_quota_definition_importer_create(imported_fields_match):
    assert imported_fields_match(
        factories.QuotaDefinitionFactory.build(
            order_number=factories.QuotaOrderNumberFactory.create(),
            monetary_unit=factories.MonetaryUnitFactory.create(),
            measurement_unit=factories.MeasurementUnitFactory.create(),
            measurement_unit_qualifier=factories.MeasurementUnitQualifierFactory.create(),
        ),
        serializers.QuotaDefinitionImporterSerializer,
    )


def test_quota_definition_importer_update(update_imported_fields_match):
    assert update_imported_fields_match(
        factories.QuotaDefinitionFactory,
        serializers.QuotaDefinitionImporterSerializer,
        dependencies={
            "order_number": factories.QuotaOrderNumberFactory,
            "monetary_unit": factories.MonetaryUnitFactory,
            "measurement_unit": factories.MeasurementUnitFactory,
            "measurement_unit_qualifier": factories.MeasurementUnitQualifierFactory,
        },
    )


def test_quota_association_importer_create(imported_fields_match):
    assert imported_fields_match(
        factories.QuotaAssociationFactory.build(
            main_quota=factories.QuotaDefinitionFactory.create(),
            sub_quota=factories.QuotaDefinitionFactory.create(),
        ),
        serializers.QuotaAssociationSerializer,
    )


def test_quota_association_importer_update(update_imported_fields_match):
    assert update_imported_fields_match(
        factories.QuotaAssociationFactory,
        serializers.QuotaAssociationSerializer,
        dependencies={
            "main_quota": factories.QuotaDefinitionFactory,
            "sub_quota": factories.QuotaDefinitionFactory,
        },
        validity=False,
    )


def test_quota_suspension_importer_create(imported_fields_match):
    assert imported_fields_match(
        factories.QuotaSuspensionFactory.build(
            quota_definition=factories.QuotaDefinitionFactory.create()
        ),
        serializers.QuotaSuspensionSerializer,
    )


def test_quota_suspension_importer_update(update_imported_fields_match, date_ranges):
    assert update_imported_fields_match(
        factories.QuotaSuspensionFactory,
        serializers.QuotaSuspensionSerializer,
        dependencies={
            "quota_definition": factories.QuotaDefinitionFactory,
        },
        validity=[date_ranges.normal, date_ranges.adjacent_later],
    )


def test_quota_blocking_importer_create(imported_fields_match):
    assert imported_fields_match(
        factories.QuotaBlockingFactory.build(
            quota_definition=factories.QuotaDefinitionFactory.create()
        ),
        serializers.QuotaBlockingSerializer,
    )


def test_quota_blocking_importer_update(update_imported_fields_match, date_ranges):
    assert update_imported_fields_match(
        factories.QuotaBlockingFactory,
        serializers.QuotaBlockingSerializer,
        dependencies={
            "quota_definition": factories.QuotaDefinitionFactory,
        },
        validity=[date_ranges.normal, date_ranges.adjacent_later],
    )


@pytest.mark.parametrize("subrecord_code", ["00", "05", "10", "15", "20", "25", "30"])
def test_quota_event_importer_create(subrecord_code, valid_user, imported_fields_match):
    assert imported_fields_match(
        factories.QuotaEventFactory.build(
            quota_definition=factories.QuotaDefinitionFactory.create(),
            subrecord_code=subrecord_code,
        ),
        serializers.QuotaEventSerializer,
    )


@pytest.mark.parametrize("subrecord_code", ["00", "05", "10", "15", "20", "25", "30"])
def test_quota_event_importer_update(subrecord_code, update_imported_fields_match):
    assert update_imported_fields_match(
        factories.QuotaEventFactory,
        serializers.QuotaEventSerializer,
        dependencies={
            "quota_definition": factories.QuotaDefinitionFactory,
        },
        kwargs={"subrecord_code": subrecord_code},
        validity=False,
    )
