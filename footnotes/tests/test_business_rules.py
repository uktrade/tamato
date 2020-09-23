import pytest
from django.core.exceptions import ValidationError
from django.db import DataError
from django.db import IntegrityError

from common.tests import factories
from common.tests.util import requires_commodities
from common.tests.util import requires_measures
from common.tests.util import requires_meursing_tables
from workbaskets.validators import WorkflowStatus


pytestmark = pytest.mark.django_db


# Footnote Type


def test_FOT1():
    """The type of the footnote must be unique"""

    t = factories.FootnoteTypeFactory()

    with pytest.raises(IntegrityError):
        factories.FootnoteTypeFactory(footnote_type_id=t.footnote_type_id)


def test_FOT2():
    """The footnote type cannot be deleted if it is used in a footnote"""

    t = factories.FootnoteTypeFactory()
    factories.FootnoteFactory(footnote_type=t)

    with pytest.raises(IntegrityError):
        t.delete()


def test_FOT3(date_ranges):
    """The start date must be less than or equal to the end date"""

    with pytest.raises(DataError):
        factories.FootnoteTypeFactory(valid_between=date_ranges.backwards)


# Footnote


def test_FO2(approved_workbasket):
    """The combination footnote type and code must be unique."""

    workbasket = factories.WorkBasketFactory()
    t = factories.FootnoteTypeFactory(workbasket=approved_workbasket)
    f = factories.FootnoteFactory(footnote_type=t, workbasket=approved_workbasket)
    factories.FootnoteFactory(
        footnote_id=f.footnote_id, footnote_type=t, workbasket=workbasket
    )
    with pytest.raises(ValidationError):
        workbasket.submit_for_approval()


def test_FO3(date_ranges):
    """The start date must be less than or equal to the end date"""

    with pytest.raises(DataError):
        factories.FootnoteFactory(valid_between=date_ranges.backwards)


def test_FO4_one_description_mandatory():
    """At least one description record is mandatory."""

    workbasket = factories.WorkBasketFactory()
    f = factories.FootnoteFactory.create(workbasket=workbasket)

    with pytest.raises(ValidationError):
        workbasket.submit_for_approval()


def test_FO4_first_description_must_have_same_start_date(date_ranges):
    """The start date of the first description period must be equal to the start date of
    the footnote.
    """

    footnote = factories.FootnoteFactory(valid_between=date_ranges.no_end)

    with pytest.raises(ValidationError):
        factories.FootnoteDescriptionFactory(
            described_footnote=footnote, valid_between=date_ranges.later
        )


def test_FO4_start_dates_cannot_match(approved_workbasket):
    """No two associated description periods may have the same start date."""

    footnote = factories.FootnoteFactory(workbasket=approved_workbasket)
    description = factories.FootnoteDescriptionFactory(
        described_footnote=footnote,
        valid_between=footnote.valid_between,
        workbasket=approved_workbasket,
    )

    workbasket = factories.WorkBasketFactory()
    factories.FootnoteDescriptionFactory.create(
        described_footnote=footnote,
        valid_between=description.valid_between,
        workbasket=workbasket,
    )
    with pytest.raises(ValidationError):
        workbasket.submit_for_approval()


def test_FO4_description_start_before_footnote_end(date_ranges):
    """The start date must be less than or equal to the end date of the footnote."""

    footnote = factories.FootnoteFactory(
        valid_between=date_ranges.normal,
        footnote_type=factories.FootnoteTypeFactory(valid_between=date_ranges.big),
    )
    factories.FootnoteDescriptionFactory(
        described_footnote=footnote, valid_between=date_ranges.starts_with_normal
    )

    with pytest.raises(ValidationError):
        factories.FootnoteDescriptionFactory(
            described_footnote=footnote, valid_between=date_ranges.later
        )


@requires_measures
def test_FO5():
    """When a footnote is used in a measure the validity period of the footnote must
    span the validity period of the measure.
    """


@requires_commodities
def test_FO6():
    """When a footnote is used in a goods nomenclature the validity period of the
    footnote must span the validity period of the association with the goods
    nomenclature.
    """


@requires_commodities
def test_FO7():
    """When a footnote is used in an export refund nomenclature code the validity period
    of the footnote must span the validity period of the association with the export
    refund code.
    """


@pytest.mark.skip(reason="Additional codes not implemented")
def test_FO9():
    """When a footnote is used in an additional code the validity period of the footnote
    must span the validity period of the association with the additional code.
    """
    pass


@requires_meursing_tables
def test_FO10():
    """When a footnote is used in a meursing table heading the validity period of the
    footnote must span the validity period of the association with the meursing heading.
    """


def test_FO17(date_ranges):
    """The validity period of the footnote type must span the validity period of the
    footnote.
    """

    t = factories.FootnoteTypeFactory(valid_between=date_ranges.normal)
    with pytest.raises(ValidationError):
        factories.FootnoteFactory(
            footnote_type=t, valid_between=date_ranges.overlap_normal
        )


@requires_measures
def test_FO11():
    """When a footnote is used in a measure then the footnote may not be deleted."""


@requires_commodities
def test_FO12():
    """When a footnote is used in a goods nomenclature then the footnote may not be
    deleted.
    """


@requires_commodities
def test_FO13():
    """When a footnote is used in an export refund code then the footnote may not be
    deleted.
    """


@pytest.mark.skip(reason="Additional codes not implemented")
def test_FO15():
    """When a footnote is used in an additional code then the footnote may not be
    deleted.
    """


@requires_meursing_tables
def test_FO16():
    """When a footnote is used in a meursing table heading then the footnote may not be
    deleted.
    """
