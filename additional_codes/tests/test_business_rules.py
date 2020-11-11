import pytest
from django.core.exceptions import ObjectDoesNotExist
from django.core.exceptions import ValidationError
from django.db import DataError
from django.db import IntegrityError

from common.tests import factories
from common.tests.util import requires_meursing_tables


pytestmark = pytest.mark.django_db


# Additional Code Type


def test_CT1():
    """
    The additional code type must be unique.
    """

    t = factories.AdditionalCodeTypeFactory.create()
    with pytest.raises(IntegrityError):
        factories.AdditionalCodeTypeFactory.create(sid=t.sid)


@requires_meursing_tables
def test_CT2():
    """
    The Meursing table plan can only be entered if the additional code type has as
    application code "Meursing table additional code type".
    """


@requires_meursing_tables
def test_CT3():
    """The Meursing table plan must exist."""


def test_CT4(date_ranges):
    """The start date must be less than or equal to the end date."""
    with pytest.raises(DataError):
        factories.AdditionalCodeTypeFactory.create(valid_between=date_ranges.backwards)


# Additional Code


def test_ACN1():
    """
    The combination of additional code type + additional code + start date must be
    unique.
    """
    ac = factories.AdditionalCodeFactory.create()

    with pytest.raises(IntegrityError):
        factories.AdditionalCodeFactory.create(
            code=ac.code, type=ac.type, valid_between=ac.valid_between
        )


def test_ACN2(must_exist):
    """
    The referenced additional code type must exist and have as application code "non-
    Meursing" or "Export Refund for Processed Agricultural Goods”.
    """
    assert must_exist(
        "type",
        factories.AdditionalCodeFactory,
    )

    with pytest.raises(ValidationError):
        factories.AdditionalCodeFactory.create(
            type__application_code=0,
        )


def test_ACN3(date_ranges):
    """
    The start date of the additional code must be less than or equal to the end date.
    """

    with pytest.raises(DataError):
        factories.AdditionalCodeFactory.create(valid_between=date_ranges.backwards)


@pytest.mark.skip(reason="This duplicates ACN1")
def test_ACN4():
    """
    The validity period of the additional code must not overlap any other additional
    code with the same additional code type + additional code + start date.
    """


@requires_meursing_tables
def text_ACN12():
    """
    When the additional code is used to represent an additional code line table
    component then the validity period of the additional code must span the validity
    period of the component.
    """


def test_ACN13(validity_period_contained):
    """
    When an additional code is used in an additional code nomenclature measure then the
    validity period of the additional code must span the validity period of the measure.
    """
    # covered by ME115

    assert validity_period_contained(
        "additional_code", factories.AdditionalCodeFactory, factories.MeasureFactory
    )


def test_ACN17(date_ranges):
    """
    The validity period of the additional code type must span the validity period of the
    additional code.
    """

    t = factories.AdditionalCodeTypeFactory(valid_between=date_ranges.normal)
    with pytest.raises(ValidationError):
        factories.AdditionalCodeFactory(
            type=t, valid_between=date_ranges.overlap_normal
        )


# Footnote association


footnote_association = pytest.mark.skip(reason="Footnote association is not required.")


@footnote_association
def test_ACN6():
    """The footnotes that are referenced must exist."""


@footnote_association
def test_ACN7():
    """
    The start date of the footnote association must be less than or equal to the end
    date of the footnote association.
    """


@footnote_association
def test_ACN8():
    """
    The period of the association with a footnote must be within (inclusive) the
    validity period of the additional code.
    """


@footnote_association
def test_ACN9():
    """
    The period of the association with a footnote must be within (inclusive) the
    validity period of the footnote.
    """


@footnote_association
def test_ACN10():
    """
    When the same footnote is associated more than once with the same additional code
    then there may be no overlap in their association periods.
    """


@footnote_association
def test_ACN11():
    """
    The referenced footnote must have a footnote type with application type =
    "non-Meursing additional code footnotes".
    """


# Additional Code Description and Description Periods


def test_ACN5_one_description_mandatory():
    """At least one description is mandatory."""

    workbasket = factories.WorkBasketFactory()
    factories.AdditionalCodeFactory(workbasket=workbasket)

    with pytest.raises(ValidationError):
        workbasket.submit_for_approval()


def test_ACN5_first_description_must_have_same_start_date(date_ranges):
    """
    The start date of the first description period must be equal to the start date of
    the additional code.
    """

    additional_code = factories.AdditionalCodeFactory(valid_between=date_ranges.no_end)

    with pytest.raises(ValidationError):
        factories.AdditionalCodeDescriptionFactory(
            described_additional_code=additional_code, valid_between=date_ranges.later
        )


def test_ACN5_start_dates_cannot_match(date_ranges):
    """No two associated description periods may have the same start date."""

    additional_code = factories.AdditionalCodeFactory(valid_between=date_ranges.no_end)

    factories.AdditionalCodeDescriptionFactory(
        described_additional_code=additional_code, valid_between=date_ranges.no_end
    )
    with pytest.raises(ValidationError):
        factories.AdditionalCodeDescriptionFactory(
            described_additional_code=additional_code, valid_between=date_ranges.no_end
        )


def test_ACN5_(date_ranges):
    """
    The start date must be less than or equal to the end date of the additional code.
    """

    ac = factories.AdditionalCodeFactory(
        valid_between=date_ranges.normal,
        type=factories.AdditionalCodeTypeFactory(valid_between=date_ranges.big),
    )
    factories.AdditionalCodeDescriptionFactory(
        described_additional_code=ac, valid_between=date_ranges.starts_with_normal
    )

    with pytest.raises(ValidationError):
        factories.AdditionalCodeDescriptionFactory(
            described_additional_code=ac, valid_between=date_ranges.later
        )


# Delete an additional code
def test_ACN14():
    """
    An additional code cannot be deleted if it is used in an additional code
    nomenclature measure.
    """

    assoc = factories.AdditionalCodeTypeMeasureTypeFactory()
    additional_code = factories.AdditionalCodeFactory(type=assoc.additional_code_type)
    measure = factories.MeasureFactory(
        measure_type=assoc.measure_type, additional_code=additional_code
    )

    with pytest.raises(IntegrityError):
        additional_code.delete()


@requires_meursing_tables
def test_ACN15():
    """
    An additional code cannot be deleted if it is used in an additional code line
    table component.
    """
