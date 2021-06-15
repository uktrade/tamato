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
    ["factory", "description_factory"],
    [
        (factories.AdditionalCodeTypeFactory, None),
        (factories.AdditionalCodeFactory, factories.AdditionalCodeDescriptionFactory),
        (factories.AdditionalCodeDescriptionFactory, None),
    ],
)
def test_additional_code_update_types(
    factory,
    description_factory,
    check_update_validation,
):
    assert check_update_validation(
        factory,
        description_factory=description_factory,
    )
