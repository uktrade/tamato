from datetime import date

import pytest

from common.business_rules import BusinessRuleViolation
from common.tests import factories
from common.tests.util import raises_if
from common.util import TaricDateRange
from measures import business_rules

pytestmark = pytest.mark.django_db


def test_ME67(spanning_dates):
    """The membership period of the excluded geographical area must span the
    validity period of the measure."""
    membership_period, measure_period, fully_spans = spanning_dates

    membership = factories.GeographicalMembershipFactory.create(
        valid_between=membership_period,
    )
    exclusion = factories.MeasureExcludedGeographicalAreaFactory.create(
        excluded_geographical_area=membership.member,
        modified_measure__geographical_area=membership.geo_group,
        modified_measure__valid_between=measure_period,
    )
    with raises_if(BusinessRuleViolation, not fully_spans):
        business_rules.ME67(exclusion.transaction).validate(exclusion)


def test_ME67_multiple_member_periods():
    """This test verifies that when a member is added and removed multiple
    times, that the rule performs correctly."""
    TaricDateRange(date(2020, 1, 1), date(2020, 12, 31))

    # membership periods
    membership_1_valid_between = TaricDateRange(
        date(2020, 1, 1),
        date(2020, 5, 31),
    )  # full first included period
    membership_2_valid_between = TaricDateRange(
        date(2020, 7, 1),
        date(2020, 12, 31),
    )  # full last included period

    # valid exclusion periods
    exclusion_valid_1_valid_between = TaricDateRange(
        date(2020, 1, 1),
        date(2020, 5, 31),
    )  # full first included period
    exclusion_valid_2_valid_between = TaricDateRange(
        date(2020, 7, 1),
        date(2020, 12, 31),
    )  # full last included period
    exclusion_valid_3_valid_between = TaricDateRange(
        date(2020, 1, 5),
        date(2020, 5, 26),
    )  # inside first period
    exclusion_valid_4_valid_between = TaricDateRange(
        date(2020, 7, 5),
        date(2020, 12, 26),
    )  # inside second period

    # invalid exclusion periods
    exclusion_invalid_1_valid_between = TaricDateRange(
        date(2020, 1, 1),
        date(2020, 6, 1),
    )  # overlap on upper by one day
    exclusion_invalid_2_valid_between = TaricDateRange(
        date(2020, 6, 30),
        date(2020, 12, 31),
    )  # overlap on lower by one day
    exclusion_invalid_3_valid_between = TaricDateRange(
        date(2020, 6, 1),
        date(2020, 6, 30),
    )  # mirror missing member period
    exclusion_invalid_4_valid_between = TaricDateRange(
        date(2020, 6, 5),
        date(2020, 6, 25),
    )  # inside missing member period

    # member kenya is available between 1/1/2020 and 31/5/2020 and then 1/7/2020 to 31/12/2020,
    # leaving 1 month (june) without kenya as a member
    membership_1 = factories.GeographicalMembershipFactory.create(
        valid_between=membership_1_valid_between,
    )

    factories.GeographicalMembershipFactory.create(
        valid_between=membership_2_valid_between,
        member=membership_1.member,
        geo_group=membership_1.geo_group,
    )

    exclusion_1_pass = factories.MeasureExcludedGeographicalAreaFactory.create(
        excluded_geographical_area=membership_1.member,
        modified_measure__geographical_area=membership_1.geo_group,
        modified_measure__valid_between=exclusion_valid_1_valid_between,
    )

    exclusion_2_pass = factories.MeasureExcludedGeographicalAreaFactory.create(
        excluded_geographical_area=membership_1.member,
        modified_measure__geographical_area=membership_1.geo_group,
        modified_measure__valid_between=exclusion_valid_2_valid_between,
    )

    exclusion_3_pass = factories.MeasureExcludedGeographicalAreaFactory.create(
        excluded_geographical_area=membership_1.member,
        modified_measure__geographical_area=membership_1.geo_group,
        modified_measure__valid_between=exclusion_valid_3_valid_between,
    )

    exclusion_4_pass = factories.MeasureExcludedGeographicalAreaFactory.create(
        excluded_geographical_area=membership_1.member,
        modified_measure__geographical_area=membership_1.geo_group,
        modified_measure__valid_between=exclusion_valid_4_valid_between,
    )

    exclusion_1_fail = factories.MeasureExcludedGeographicalAreaFactory.create(
        excluded_geographical_area=membership_1.member,
        modified_measure__geographical_area=membership_1.geo_group,
        modified_measure__valid_between=exclusion_invalid_1_valid_between,
    )

    exclusion_2_fail = factories.MeasureExcludedGeographicalAreaFactory.create(
        excluded_geographical_area=membership_1.member,
        modified_measure__geographical_area=membership_1.geo_group,
        modified_measure__valid_between=exclusion_invalid_2_valid_between,
    )

    exclusion_3_fail = factories.MeasureExcludedGeographicalAreaFactory.create(
        excluded_geographical_area=membership_1.member,
        modified_measure__geographical_area=membership_1.geo_group,
        modified_measure__valid_between=exclusion_invalid_3_valid_between,
    )

    exclusion_4_fail = factories.MeasureExcludedGeographicalAreaFactory.create(
        excluded_geographical_area=membership_1.member,
        modified_measure__geographical_area=membership_1.geo_group,
        modified_measure__valid_between=exclusion_invalid_4_valid_between,
    )

    business_rules.ME67(exclusion_1_pass.transaction).validate(exclusion_1_pass)
    business_rules.ME67(exclusion_2_pass.transaction).validate(exclusion_2_pass)
    business_rules.ME67(exclusion_2_pass.transaction).validate(exclusion_3_pass)
    business_rules.ME67(exclusion_2_pass.transaction).validate(exclusion_4_pass)

    with pytest.raises(BusinessRuleViolation) as e:
        business_rules.ME67(exclusion_1_fail.transaction).validate(exclusion_1_fail)
        assert str(e) == "<ExceptionInfo for raises contextmanager>"

    with pytest.raises(BusinessRuleViolation) as e:
        business_rules.ME67(exclusion_2_fail.transaction).validate(exclusion_2_fail)
        assert str(e) == "<ExceptionInfo for raises contextmanager>"

    with pytest.raises(BusinessRuleViolation) as e:
        business_rules.ME67(exclusion_3_fail.transaction).validate(exclusion_3_fail)
        assert str(e) == "<ExceptionInfo for raises contextmanager>"

    with pytest.raises(BusinessRuleViolation) as e:
        business_rules.ME67(exclusion_4_fail.transaction).validate(exclusion_4_fail)
        assert str(e) == "<ExceptionInfo for raises contextmanager>"
