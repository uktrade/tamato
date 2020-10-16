from datetime import datetime
from datetime import timezone

import django
import pytest
from django.core.exceptions import ValidationError
from django.db import DataError

from common.tests import factories
from common.tests.util import only_applicable_after
from regulations import models


pytestmark = pytest.mark.django_db


def test_ROIMB1(unique_identifying_fields):
    """The (regulation id + role id) must be unique."""
    # Effectively this means that the regulation ID needs to be unique as we are always
    # going to be using role ID 1.

    assert unique_identifying_fields(factories.RegulationFactory)


def test_ROIMB3(date_ranges):
    """The start date must be less than or equal to the end date."""
    # In the UK, legislation will be rarely end-dated.

    with pytest.raises(DataError):
        factories.RegulationFactory(valid_between=date_ranges.backwards)


def test_ROIMB4(must_exist):
    """The referenced regulation group must exist."""

    assert must_exist(
        "regulation_group",
        factories.RegulationGroupFactory,
        factories.RegulationFactory,
    )


@pytest.mark.skip(reason="Not using regulation replacement functionality")
def test_ROIMB5():
    """If the regulation is replaced, completely or partially, modification is allowed
    only on the fields "Publication Date", "Official journal Number", "Official journal
    Page" and "Regulation Group Id".
    """
    pass


@pytest.mark.skip(reason="Not using regulation abrogation functionality")
def test_ROIMB6():
    """If the regulation is abrogated, completely or explicitly, modification is allowed
    only on the fields "Publication Date", "Official journal Number", "Official journal
    Page" and "Regulation Group Id".
    """
    pass


@pytest.mark.skip(reason="Not using regulation prorogation functionality")
def test_ROIMB7():
    """If the regulation is prorogated, modification is allowed only on the fields
    "Publication Date", "Official journal Number", "Official journal Page" and
    "Regulation Group Id".
    """
    pass


def test_ROIMB8(date_ranges):
    """Explicit dates of related measures must be within the validity period of the base
    regulation.

    Only applicable for measures with start date after 31/12/2003."""

    with pytest.raises(ValidationError):
        factories.MeasureFactory(
            generating_regulation__valid_between=date_ranges.starts_with_normal,
            valid_between=date_ranges.normal,
        )


@pytest.mark.xfail(reason="ME87 catches this currently")
def test_ROIMB8_before_cutoff(date_ranges):
    cutoff = datetime(2003, 12, 31, tzinfo=timezone.utc)

    factories.MeasureFactory(
        generating_regulation__valid_between=date_ranges.short_before(cutoff),
        valid_between=date_ranges.medium_before(cutoff),
        geographical_area__valid_between=date_ranges.medium_before(cutoff),
        goods_nomenclature__valid_between=date_ranges.medium_before(cutoff),
        measure_type__valid_between=date_ranges.medium_before(cutoff),
        measure_type__measure_type_series__valid_between=date_ranges.medium_before(
            cutoff
        ),
    )


@pytest.mark.skip(reason="Not using effective end date")
def test_ROIMB48():
    """If the regulation has not been abrogated, the effective end date must be greater
    than or equal to the base regulation end date if it is explicit.
    """
    pass


@pytest.mark.skip(reason="Not implemented yet")
@pytest.mark.parametrize(
    "id, approved, expect_error, cannot_change",
    [
        ("C2000000", False, False, False),
        ("C2000000", True, False, True),
        ("R2000000", False, True, True),
        ("R2000000", True, False, True),
    ],
)
def test_ROIMB44(id, approved, expect_error, cannot_change):
    """The "Regulation Approved Flag" indicates for a draft regulation whether the draft
    is approved, i.e. the regulation is definitive apart from its publication (only the
    definitive regulation id and the O.J.  reference are not yet known).  A draft
    regulation (regulation id starts with a 'C') can have its "Regulation Approved Flag"
    set to 0='Not Approved' or 1='Approved'. Its flag can only change from 0='Not
    Approved' to 1='Approved'. Any other regulation must have its "Regulation Approved
    Flag" set to 1='Approved'."""
    # We need to work on the draft –> live status however, as we have not yet worked
    # this through
    with raises_if(ValidationError, expect_error):
        r = factories.RegulationFactory.create(regulation_id=id, approved=approved)
        with raises_if(ValidationError, cannot_change):
            r.approved = not r.approved
            r.save()


@pytest.mark.skip(reason="Not implemented yet")
def test_ROIMB46():
    """A base regulation cannot be deleted if it is used as a justification regulation,
    except for ‘C’ regulations used only in measures as both measure-generating
    regulation and justification regulation."""
    # We should not be deleting base regulations. Also, we will not be using the
    # justification regulation field, though there will be a lot of EU regulations where
    # the justification regulation field is set.
    pass


def test_ROIMB47(validity_period_contained):
    """The validity period of the regulation group id must span the validity period of
    the base regulation."""
    # But we will be ensuring that the regulation groups are not end dated, therefore we
    # will not get hit by this

    assert validity_period_contained(
        "regulation_group",
        factories.RegulationGroupFactory,
        factories.RegulationFactory,
    )
