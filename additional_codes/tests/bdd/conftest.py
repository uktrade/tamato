from pytest_bdd import given

from common.tests import factories
from common.tests.util import Dates


@given("additional code X000")
def additional_code_X000():
    t = factories.AdditionalCodeTypeFactory(sid="X", valid_between=Dates.big)
    ac = factories.AdditionalCodeFactory(code="000", type=t, valid_between=Dates.normal)
    factories.AdditionalCodeDescriptionFactory(
        described_additional_code=ac,
        description="This is X000",
        valid_between=Dates.starts_with_normal,
    )
    factories.AdditionalCodeDescriptionFactory(
        described_additional_code=ac,
        description="Another description",
        valid_between=Dates.overlap_normal,
    )
    return ac
