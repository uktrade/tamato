import pytest
from pytest_bdd import given

from common.tests import factories

pytestmark = pytest.mark.django_db


@given("additional code X000", target_fixture="additional_code_X000")
def additional_code_X000(date_ranges):
    t = factories.AdditionalCodeTypeFactory.create(
        sid="X",
        valid_between=date_ranges.big,
    )
    ac = factories.AdditionalCodeFactory.create(
        code="000",
        type=t,
        valid_between=date_ranges.normal,
    )
    factories.AdditionalCodeDescriptionFactory.create(
        described_additionalcode=ac,
        description="This is X000",
        validity_start=date_ranges.starts_with_normal.lower,
    )
    factories.AdditionalCodeDescriptionFactory.create(
        described_additionalcode=ac,
        description="Another description",
        validity_start=date_ranges.overlap_normal.lower,
    )
    return ac


@given("a previous additional code X000", target_fixture="old_additional_code")
def old_additional_code(date_ranges, additional_code_X000):
    ac = factories.AdditionalCodeFactory.create(
        code=additional_code_X000.code,
        type=additional_code_X000.type,
        valid_between=date_ranges.earlier,
    )
    factories.AdditionalCodeDescriptionFactory.create(
        described_additionalcode=ac,
        description="This was an older usage of X000",
        validity_start=date_ranges.earlier.lower,
    )
    return ac
