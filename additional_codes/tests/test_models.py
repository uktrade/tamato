import pytest

from common.tests import factories

pytestmark = pytest.mark.django_db


def test_additional_code_in_use(in_use_check_respects_deletes):
    assert in_use_check_respects_deletes(
        factories.AdditionalCodeFactory,
        "in_use",
        factories.MeasureFactory,
        "additional_code",
    )


def test_additional_code_update_types(check_update_validation):
    assert check_update_validation(factories.AdditionalCodeTypeFactory)
    assert check_update_validation(
        factories.AdditionalCodeFactory,
        description_factory=factories.AdditionalCodeDescriptionFactory,
    )
    assert check_update_validation(factories.AdditionalCodeDescriptionFactory)
