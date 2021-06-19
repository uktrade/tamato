import pytest

from common.tests import factories

pytestmark = pytest.mark.django_db


def test_quota_order_number_importer(imported_fields_match):
    assert imported_fields_match(
        factories.QuotaOrderNumberFactory,
    )


def test_quota_order_number_origin_importer(imported_fields_match):
    assert imported_fields_match(
        factories.QuotaOrderNumberOriginFactory,
        dependencies={
            "order_number": factories.QuotaOrderNumberFactory,
            "geographical_area": factories.GeographicalAreaFactory,
        },
    )


def test_quota_order_number_origin_exclusion_importer(
    imported_fields_match,
):
    assert imported_fields_match(
        factories.QuotaOrderNumberOriginExclusionFactory,
        dependencies={
            "origin": factories.QuotaOrderNumberOriginFactory,
            "excluded_geographical_area": factories.GeographicalAreaFactory,
        },
    )


def test_quota_definition_importer(imported_fields_match):
    assert imported_fields_match(
        factories.QuotaDefinitionFactory,
        dependencies={
            "order_number": factories.QuotaOrderNumberFactory,
            "monetary_unit": factories.MonetaryUnitFactory,
            "measurement_unit": factories.MeasurementUnitFactory,
            "measurement_unit_qualifier": factories.MeasurementUnitQualifierFactory,
        },
    )


def test_quota_association_importer(imported_fields_match):
    assert imported_fields_match(
        factories.QuotaAssociationFactory,
        dependencies={
            "main_quota": factories.QuotaDefinitionFactory,
            "sub_quota": factories.QuotaDefinitionFactory,
        },
    )


def test_quota_suspension_importer(imported_fields_match, date_ranges):
    assert imported_fields_match(
        factories.QuotaSuspensionFactory,
        dependencies={
            "quota_definition": factories.QuotaDefinitionFactory,
        },
    )


def test_quota_blocking_importer(imported_fields_match, date_ranges):
    assert imported_fields_match(
        factories.QuotaBlockingFactory,
        dependencies={
            "quota_definition": factories.QuotaDefinitionFactory,
        },
    )


@pytest.mark.parametrize("subrecord_code", ["00", "05", "10", "15", "20", "25", "30"])
def test_quota_event_importer(subrecord_code, imported_fields_match):
    assert imported_fields_match(
        factories.QuotaEventFactory,
        dependencies={
            "quota_definition": factories.QuotaDefinitionFactory,
            "subrecord_code": subrecord_code,
        },
    )
