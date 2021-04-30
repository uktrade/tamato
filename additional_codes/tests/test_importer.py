import pytest

from additional_codes import serializers
from common.tests import factories

pytestmark = pytest.mark.django_db


def test_additional_code_type_importer_create(imported_fields_match):
    assert imported_fields_match(
        factories.AdditionalCodeTypeFactory,
        serializers.AdditionalCodeTypeSerializer,
    )


def test_additional_code_type_importer_update(update_imported_fields_match):
    assert update_imported_fields_match(
        factories.AdditionalCodeTypeFactory,
        serializers.AdditionalCodeTypeSerializer,
    )


def test_additional_code_importer_create(imported_fields_match):
    assert imported_fields_match(
        factories.AdditionalCodeFactory.build(
            type=factories.AdditionalCodeTypeFactory.create(),
        ),
        serializers.AdditionalCodeSerializer,
    )


def test_additional_code_importer_update(update_imported_fields_match):
    assert update_imported_fields_match(
        factories.AdditionalCodeFactory,
        serializers.AdditionalCodeSerializer,
        dependencies={"type": factories.AdditionalCodeTypeFactory},
    )


def test_additional_code_description_importer_create(imported_fields_match):
    assert imported_fields_match(
        factories.AdditionalCodeDescriptionFactory.build(
            described_additionalcode=factories.AdditionalCodeFactory.create(),
        ),
        serializers.AdditionalCodeDescriptionSerializer,
    )


def test_additional_code_description_importer_update(update_imported_fields_match):
    assert update_imported_fields_match(
        factories.AdditionalCodeDescriptionFactory,
        serializers.AdditionalCodeDescriptionSerializer,
        dependencies={"described_additionalcode": factories.AdditionalCodeFactory},
    )
