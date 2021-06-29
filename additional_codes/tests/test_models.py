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


@pytest.mark.parametrize(
    "factory",
    [
        factories.AdditionalCodeTypeFactory,
        factories.AdditionalCodeFactory,
        factories.AdditionalCodeDescriptionFactory,
        factories.FootnoteAssociationAdditionalCodeFactory,
    ],
)
def test_additional_code_update_types(
    factory,
    check_update_validation,
):
    assert check_update_validation(
        factory,
    )
