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
