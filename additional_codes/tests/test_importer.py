import pytest

from additional_codes import serializers
from common.tests import factories

pytestmark = pytest.mark.django_db


def test_additional_code_type_importer(imported_fields_match):
    assert imported_fields_match(
        factories.AdditionalCodeTypeFactory,
        serializers.AdditionalCodeTypeSerializer,
    )


def test_additional_code_importer(imported_fields_match):
    assert imported_fields_match(
        factories.AdditionalCodeFactory,
        serializers.AdditionalCodeSerializer,
        dependencies={"type": factories.AdditionalCodeTypeFactory},
    )


def test_additional_code_description_importer(imported_fields_match):
    assert imported_fields_match(
        factories.AdditionalCodeDescriptionFactory,
        serializers.AdditionalCodeDescriptionSerializer,
        dependencies={"described_additionalcode": factories.AdditionalCodeFactory},
    )
