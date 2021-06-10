import pytest
from django.db import DataError

from additional_codes import business_rules
from additional_codes import models
from additional_codes.validators import ApplicationCode
from common.business_rules import BusinessRuleViolation
from common.tests import factories
from common.tests.util import raises_if
from common.tests.util import requires_meursing_tables

pytestmark = pytest.mark.django_db


# Additional Code Type


@pytest.mark.xfail(reason="CT1 disabled")
def test_CT1(assert_handles_duplicates):
    """The additional code type must be unique."""

    assert_handles_duplicates(
        factories.AdditionalCodeTypeFactory,
        business_rules.CT1,
    )


@requires_meursing_tables
def test_CT2():
    """The Meursing table plan can only be entered if the additional code type
    has as application code "Meursing table additional code type"."""

    assert False


@requires_meursing_tables
def test_CT3():
    """The Meursing table plan must exist."""

    assert False


def test_CT4(date_ranges):
    """The start date must be less than or equal to the end date."""
    with pytest.raises(DataError):
        factories.AdditionalCodeTypeFactory.create(valid_between=date_ranges.backwards)


# Additional Code


def test_ACN1(assert_handles_duplicates):
    """The combination of additional code type + additional code + start date
    must be unique."""

    assert_handles_duplicates(
        factories.AdditionalCodeFactory,
        business_rules.ACN1,
        identifying_fields=["code", "type", "valid_between__lower"],
    )


def test_ACN2_type_must_exist(reference_nonexistent_record):
    """The referenced additional code type must exist."""

    with pytest.raises(models.AdditionalCodeType.DoesNotExist):
        with reference_nonexistent_record(
            factories.AdditionalCodeFactory,
            "type",
        ) as ac:
            assert ac.type is None


@pytest.mark.parametrize(
    "app_code, expect_error",
    [
        (ApplicationCode.EXPORT_REFUND_NOMENCLATURE, True),
        (ApplicationCode.ADDITIONAL_CODES, False),
        (ApplicationCode.MEURSING_ADDITIONAL_CODES, True),
        (ApplicationCode.EXPORT_REFUND_AGRI, False),
    ],
)
def test_ACN2_allowed_application_codes(app_code, expect_error):
    """The referenced additional code type must have as application code "non-
    Meursing" or "Export Refund for Processed Agricultural Goods”."""
    additional_code = factories.AdditionalCodeFactory.create(
        type__application_code=app_code,
    )
    with raises_if(BusinessRuleViolation, expect_error):
        business_rules.ACN2(additional_code.transaction).validate(additional_code)


def test_ACN3(date_ranges):
    """The start date of the additional code must be less than or equal to the
    end date."""

    with pytest.raises(DataError):
        factories.AdditionalCodeFactory.create(valid_between=date_ranges.backwards)


def test_ACN4(date_ranges):
    """The validity period of the additional code must not overlap any other
    additional code with the same additional code type + additional code + start
    date."""
    # If they have the same start date then they overlap by definition. This is a
    # duplicate of ACN1.

    existing = factories.AdditionalCodeFactory.create(valid_between=date_ranges.normal)
    business_rules.ACN4(existing.transaction).validate(existing)

    duplicate = factories.AdditionalCodeFactory.create(
        code=existing.code,
        type=existing.type,
        valid_between=date_ranges.starts_with_normal,
    )
    with pytest.raises(BusinessRuleViolation):
        business_rules.ACN4(duplicate.transaction).validate(duplicate)


@requires_meursing_tables
def text_ACN12():
    """When the additional code is used to represent an additional code line
    table component then the validity period of the additional code must span
    the validity period of the component."""

    assert False


def test_ACN13(date_ranges):
    """When an additional code is used in an additional code nomenclature
    measure then the validity period of the additional code must span the
    validity period of the measure."""
    # covered by ME115

    measure = factories.MeasureWithAdditionalCodeFactory.create(
        additional_code__valid_between=date_ranges.normal,
        valid_between=date_ranges.overlap_normal,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.ACN13(measure.transaction).validate(measure.additional_code)


def test_ACN17(date_ranges):
    """The validity period of the additional code type must span the validity
    period of the additional code."""
    additional_code = factories.AdditionalCodeFactory.create(
        type__valid_between=date_ranges.normal,
        valid_between=date_ranges.overlap_normal,
    )
    with pytest.raises(BusinessRuleViolation):
        business_rules.ACN17(additional_code.transaction).validate(additional_code)


# Footnote association


footnote_association = pytest.mark.skip(reason="Footnote association is not required.")


@footnote_association
def test_ACN6():
    """The footnotes that are referenced must exist."""

    assert False


@footnote_association
def test_ACN7():
    """The start date of the footnote association must be less than or equal to
    the end date of the footnote association."""

    assert False


@footnote_association
def test_ACN8():
    """The period of the association with a footnote must be within (inclusive)
    the validity period of the additional code."""

    assert False


@footnote_association
def test_ACN9():
    """The period of the association with a footnote must be within (inclusive)
    the validity period of the footnote."""

    assert False


@footnote_association
def test_ACN10():
    """When the same footnote is associated more than once with the same
    additional code then there may be no overlap in their association
    periods."""

    assert False


@footnote_association
def test_ACN11():
    """The referenced footnote must have a footnote type with application type =
    "non-Meursing additional code footnotes"."""

    assert False


# Additional Code Description and Description Periods


def test_ACN5_one_description_mandatory():
    """At least one description is mandatory."""
    additional_code = factories.AdditionalCodeFactory.create()
    with pytest.raises(BusinessRuleViolation):
        business_rules.ACN5(additional_code.transaction).validate(additional_code)


def test_ACN5_first_description_must_have_same_start_date(date_ranges):
    """The start date of the first description period must be equal to the start
    date of the additional code."""

    description = factories.AdditionalCodeDescriptionFactory.create(
        described_additionalcode__valid_between=date_ranges.no_end,
        validity_start=date_ranges.later.lower,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.ACN5(description.transaction).validate(
            description.described_additionalcode,
        )


def test_ACN5_start_dates_cannot_match():
    """No two associated description periods may have the same start date."""

    existing = factories.AdditionalCodeDescriptionFactory.create()
    duplicate = factories.AdditionalCodeDescriptionFactory.create(
        described_additionalcode=existing.described_additionalcode,
        validity_start=existing.validity_start,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.ACN5(duplicate.transaction).validate(
            existing.described_additionalcode,
        )


def test_ACN5_description_start_before_additional_code_end(date_ranges):
    """The start date must be less than or equal to the end date of the
    additional code."""

    description = factories.AdditionalCodeDescriptionFactory.create(
        described_additionalcode__valid_between=date_ranges.normal,
        validity_start=date_ranges.later.lower,
    )
    next_description = factories.AdditionalCodeDescriptionFactory.create(
        described_additionalcode=description.described_additionalcode,
        validity_start=date_ranges.starts_with_normal.lower,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.ACN5(next_description.transaction).validate(
            description.described_additionalcode,
        )


def test_ACN14(delete_record):
    """An additional code cannot be deleted if it is used in an additional code
    nomenclature measure."""

    assoc = factories.AdditionalCodeTypeMeasureTypeFactory.create()
    additional_code = factories.AdditionalCodeFactory.create(
        type=assoc.additional_code_type,
    )
    measure = factories.MeasureFactory.create(
        measure_type=assoc.measure_type,
        additional_code=additional_code,
        goods_nomenclature__item_id="2000000000",
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.ACN14(measure.transaction).validate(
            delete_record(additional_code),
        )


@requires_meursing_tables
def test_ACN15():
    """An additional code cannot be deleted if it is used in an additional code
    line table component."""

    assert False
