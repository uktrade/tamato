import pytest
from pytest_bdd import given

from common.tests import factories


pytestmark = pytest.mark.django_db


@given("additional code X000", target_fixture="additional_code_X000")
def additional_code_X000(date_ranges):
    t = factories.AdditionalCodeTypeFactory(sid="X", valid_between=date_ranges.big)
    ac = factories.AdditionalCodeFactory(
        code="000", type=t, valid_between=date_ranges.normal
    )
    factories.AdditionalCodeDescriptionFactory(
        described_additional_code=ac,
        description="This is X000",
        valid_between=date_ranges.starts_with_normal,
    )
    factories.AdditionalCodeDescriptionFactory(
        described_additional_code=ac,
        description="Another description",
        valid_between=date_ranges.overlap_normal,
    )
    return ac
