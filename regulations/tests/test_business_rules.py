import pytest
from django.db import DataError

from common.business_rules import BusinessRuleViolation
from common.tests import factories
from common.tests.util import only_applicable_after
from common.tests.util import raises_if
from regulations import business_rules
from regulations.validators import RoleType

pytestmark = pytest.mark.django_db


@pytest.mark.business_rules
def test_ROIMB1(assert_handles_duplicates):
    """The (regulation id + role id) must be unique."""
    # Effectively this means that the regulation ID needs to be unique as we are always
    # going to be using role ID 1.

    assert_handles_duplicates(
        factories.BaseRegulationFactory,
        business_rules.ROIMB1,
    )


@pytest.mark.business_rules
def test_ROIMB3(date_ranges):
    """The start date must be less than or equal to the end date."""
    # In the UK, legislation will be rarely end-dated.

    with pytest.raises(DataError):
        factories.BaseRegulationFactory.create(valid_between=date_ranges.backwards)


@pytest.mark.business_rules
def test_ROIMB4(reference_nonexistent_record):
    """The referenced regulation group must exist."""

    with reference_nonexistent_record(
        factories.BaseRegulationFactory,
        "regulation_group",
    ) as regulation:
        with pytest.raises(BusinessRuleViolation):
            business_rules.ROIMB4(regulation.transaction).validate(regulation)


@pytest.mark.business_rules
@pytest.mark.skip(reason="Not using regulation replacement functionality")
def test_ROIMB5():
    """If the regulation is replaced, completely or partially, modification is
    allowed only on the fields "Publication Date", "Official journal Number",
    "Official journal Page" and "Regulation Group Id"."""
    assert False


@pytest.mark.business_rules
@pytest.mark.skip(reason="Not using regulation abrogation functionality")
def test_ROIMB6():
    """If the regulation is abrogated, completely or explicitly, modification is
    allowed only on the fields "Publication Date", "Official journal Number",
    "Official journal Page" and "Regulation Group Id"."""
    assert False


@pytest.mark.business_rules
@pytest.mark.skip(reason="Not using regulation prorogation functionality")
def test_ROIMB7():
    """If the regulation is prorogated, modification is allowed only on the
    fields "Publication Date", "Official journal Number", "Official journal
    Page" and "Regulation Group Id"."""
    assert False


@pytest.mark.business_rules
@only_applicable_after("2003-12-31")
def test_ROIMB8(date_ranges):
    """
    Explicit dates of related measures must be within the validity period of the
    base regulation.

    Only applicable for measures with start date after 31/12/2003.
    """

    measure = factories.MeasureFactory.create(
        generating_regulation=factories.BaseRegulationFactory.create(
            valid_between=date_ranges.normal,
        ),
        valid_between=date_ranges.overlap_normal,
    )
    with pytest.raises(BusinessRuleViolation):
        business_rules.ROIMB8(measure.transaction).validate(
            measure.generating_regulation,
        )


@pytest.mark.business_rules
@pytest.mark.skip(reason="Not using effective end date")
def test_ROIMB48():
    """If the regulation has not been abrogated, the effective end date must be
    greater than or equal to the base regulation end date if it is explicit."""
    assert False


@pytest.mark.business_rules
@pytest.mark.parametrize(
    "id, approved, change_flag, expect_error",
    [
        ("C2000000", False, False, False),
        ("C2000000", False, True, False),
        ("C2000000", True, False, False),
        ("C2000000", True, True, True),
        ("R2000000", False, False, True),
        ("R2000000", False, True, False),
        ("R2000000", True, False, False),
        ("R2000000", True, True, True),
    ],
)
def test_ROIMB44(id, approved, change_flag, expect_error):
    """
    The "Regulation Approved Flag" indicates for a draft regulation whether the
    draft is approved, i.e. the regulation is definitive apart from its
    publication (only the definitive regulation id and the O.J.

    reference are not yet known).  A draft regulation (regulation id starts with
    a 'C') can have its "Regulation Approved Flag" set to 0='Not Approved' or
    1='Approved'. Its flag can only change from 0='Not Approved' to
    1='Approved'. Any other regulation must have its "Regulation Approved Flag"
    set to 1='Approved'.
    """
    # We need to work on the draft –> live status however, as we have not yet worked
    # this through

    regulation = factories.RegulationFactory.create(
        regulation_id=id,
        approved=approved,
    )

    if change_flag:
        regulation = regulation.new_version(
            approved=not regulation.approved,
            workbasket=factories.WorkBasketFactory.create(),
        )

    if expect_error:
        with pytest.raises(BusinessRuleViolation):
            business_rules.ROIMB44(regulation.transaction).validate(regulation)

    else:
        business_rules.ROIMB44(regulation.transaction).validate(regulation)


@pytest.mark.business_rules
@pytest.mark.parametrize(
    ("regulation_id", "role_type", "expect_error"),
    (
        (factories.BaseRegulationFactory.regulation_id, RoleType.BASE, True),
        ("C2000000", RoleType.BASE, False),
        (factories.BaseRegulationFactory.regulation_id, RoleType.MODIFICATION, False),
    ),
)
def test_ROIMB46(regulation_id, role_type, expect_error, delete_record):
    """A base regulation cannot be deleted if it is used as a justification
    regulation, except for ‘C’ regulations used only in measures as both
    measure-generating regulation and justification regulation."""
    # We should not be deleting base regulations. Also, we will not be using the
    # justification regulation field, though there will be a lot of EU regulations where
    # the justification regulation field is set.

    regulation = factories.RegulationFactory.create(
        regulation_id=regulation_id,
        role_type=role_type,
    )
    measure = factories.MeasureFactory.create(
        valid_between=factories.date_ranges("normal"),
        generating_regulation=regulation,
        terminating_regulation=regulation,
    )
    assert measure.terminating_regulation == regulation

    deleted = delete_record(regulation)
    with raises_if(BusinessRuleViolation, expect_error):
        business_rules.ROIMB46(deleted.transaction).validate(deleted)


@pytest.mark.business_rules
def test_ROIMB47(assert_spanning_enforced):
    """The validity period of the regulation group id must span the validity
    period of the base regulation."""
    # But we will be ensuring that the regulation groups are not end dated, therefore we
    # will not get hit by this

    assert_spanning_enforced(
        factories.BaseRegulationFactory,
        business_rules.ROIMB47,
    )
