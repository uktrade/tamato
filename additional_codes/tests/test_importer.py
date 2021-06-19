import pytest

from common.tests import factories

pytestmark = pytest.mark.django_db


def test_additional_code_type_importer(imported_fields_match):
    assert imported_fields_match(
        factories.AdditionalCodeTypeFactory,
    )


def test_additional_code_importer(imported_fields_match):
    assert imported_fields_match(
        factories.AdditionalCodeFactory,
        dependencies={"type": factories.AdditionalCodeTypeFactory},
    )


def test_additional_code_description_importer(imported_fields_match):
    assert imported_fields_match(
        factories.AdditionalCodeDescriptionFactory,
        dependencies={"described_additionalcode": factories.AdditionalCodeFactory},
    )
