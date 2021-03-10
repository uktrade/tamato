import pytest
from django.db import DataError

from common.business_rules import BusinessRuleViolation
from common.tests import factories
from common.tests.util import requires_meursing_tables
from footnotes import business_rules

pytestmark = pytest.mark.django_db


# Footnote Type


def test_FOT1(make_duplicate_record):
    """The type of the footnote must be unique."""

    duplicate = make_duplicate_record(factories.FootnoteTypeFactory)

    with pytest.raises(BusinessRuleViolation):
        business_rules.FOT1(duplicate.transaction).validate(duplicate)


def test_FOT2(delete_record):
    """The footnote type cannot be deleted if it is used in a footnote."""

    footnote = factories.FootnoteFactory.create()
    deleted_record = delete_record(footnote.footnote_type)

    with pytest.raises(BusinessRuleViolation):
        business_rules.FOT2(deleted_record.transaction).validate(deleted_record)


def test_FOT3(date_ranges):
    """The start date must be less than or equal to the end date."""

    with pytest.raises(DataError):
        factories.FootnoteTypeFactory.create(valid_between=date_ranges.backwards)


# Footnote


def test_FO2(make_duplicate_record):
    """The combination footnote type and code must be unique."""

    duplicate = make_duplicate_record(factories.FootnoteFactory)

    with pytest.raises(BusinessRuleViolation):
        business_rules.FO2(duplicate.transaction).validate(duplicate)


def test_FO3(date_ranges):
    """The start date must be less than or equal to the end date."""

    with pytest.raises(DataError):
        factories.FootnoteFactory.create(valid_between=date_ranges.backwards)


def test_FO4_one_description_mandatory():
    """At least one description record is mandatory."""
    footnote = factories.FootnoteFactory.create(description=None)
    with pytest.raises(BusinessRuleViolation):
        business_rules.FO4(footnote.transaction).validate(footnote)


def test_FO4_first_description_must_have_same_start_date(date_ranges):
    """The start date of the first description period must be equal to the start
    date of the footnote."""
    footnote = factories.FootnoteFactory.create(
        description__valid_between=date_ranges.later,
    )
    with pytest.raises(BusinessRuleViolation):
        business_rules.FO4(footnote.transaction).validate(footnote)


def test_FO4_start_dates_cannot_match():
    """No two associated description periods may have the same start date."""

    footnote = factories.FootnoteFactory.create()
    duplicate = factories.FootnoteDescriptionFactory.create(
        described_footnote=footnote,
        valid_between=footnote.valid_between,
    )
    with pytest.raises(BusinessRuleViolation):
        business_rules.FO4(duplicate.transaction).validate(footnote)


def test_FO4_description_start_before_footnote_end(date_ranges):
    """The start date must be less than or equal to the end date of the
    footnote."""

    footnote = factories.FootnoteFactory.create(
        valid_between=date_ranges.normal,
        description__valid_between=date_ranges.starts_with_normal,
    )
    early_description = factories.FootnoteDescriptionFactory.create(
        described_footnote=footnote,
        valid_between=date_ranges.later,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.FO4(early_description.transaction).validate(footnote)


def test_FO5(date_ranges):
    """When a footnote is used in a measure the validity period of the footnote
    must span the validity period of the measure."""

    assoc = factories.FootnoteAssociationMeasureFactory.create(
        footnoted_measure=factories.MeasureFactory.create(
            valid_between=date_ranges.normal,
        ),
        associated_footnote__valid_between=date_ranges.starts_with_normal,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.FO5(assoc.transaction).validate(assoc.associated_footnote)


def test_FO6(date_ranges):
    """When a footnote is used in a goods nomenclature the validity period of
    the footnote must span the validity period of the association with the goods
    nomenclature."""

    assoc = factories.FootnoteAssociationGoodsNomenclatureFactory.create(
        goods_nomenclature=factories.GoodsNomenclatureFactory.create(
            valid_between=date_ranges.normal,
        ),
        associated_footnote__valid_between=date_ranges.starts_with_normal,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.FO6(assoc.transaction).validate(assoc.associated_footnote)


@pytest.mark.skip(reason="Export Refunds not implemented")
def test_FO7():
    """When a footnote is used in an export refund nomenclature code the
    validity period of the footnote must span the validity period of the
    association with the export refund code."""

    assert False


def test_FO9(date_ranges):
    """When a footnote is used in an additional code the validity period of the
    footnote must span the validity period of the association with the
    additional code."""

    assoc = factories.FootnoteAssociationAdditionalCodeFactory.create(
        additional_code=factories.AdditionalCodeFactory.create(
            valid_between=date_ranges.normal,
        ),
        associated_footnote__valid_between=date_ranges.starts_with_normal,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.FO9(assoc.transaction).validate(assoc.associated_footnote)


@requires_meursing_tables
def test_FO10():
    """When a footnote is used in a meursing table heading the validity period
    of the footnote must span the validity period of the association with the
    meursing heading."""


def test_FO17(date_ranges):
    """The validity period of the footnote type must span the validity period of
    the footnote."""
    footnote = factories.FootnoteFactory.create(
        footnote_type__valid_between=date_ranges.normal,
        valid_between=date_ranges.overlap_normal,
    )
    with pytest.raises(BusinessRuleViolation):
        business_rules.FO17(footnote.transaction).validate(footnote)


def test_FO11(delete_record):
    """When a footnote is used in a measure then the footnote may not be
    deleted."""

    assoc = factories.FootnoteAssociationMeasureFactory.create()

    with pytest.raises(BusinessRuleViolation):
        business_rules.FO11(assoc.transaction).validate(
            delete_record(assoc.associated_footnote),
        )


def test_FO12(delete_record):
    """When a footnote is used in a goods nomenclature then the footnote may not
    be deleted."""

    assoc = factories.FootnoteAssociationGoodsNomenclatureFactory.create()

    with pytest.raises(BusinessRuleViolation):
        business_rules.FO12(assoc.transaction).validate(
            delete_record(assoc.associated_footnote),
        )


@pytest.mark.skip(reason="Export Refunds not implemented")
def test_FO13():
    """When a footnote is used in an export refund code then the footnote may
    not be deleted."""

    assert False


def test_FO15(delete_record):
    """When a footnote is used in an additional code then the footnote may not
    be deleted."""

    assoc = factories.FootnoteAssociationAdditionalCodeFactory.create()

    with pytest.raises(BusinessRuleViolation):
        business_rules.FO15(assoc.transaction).validate(
            delete_record(assoc.associated_footnote),
        )


@requires_meursing_tables
def test_FO16():
    """When a footnote is used in a meursing table heading then the footnote may
    not be deleted."""
