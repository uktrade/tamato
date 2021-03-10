import pytest
from django.db import DataError

from certificates import business_rules
from common.business_rules import BusinessRuleViolation
from common.tests import factories

pytestmark = pytest.mark.django_db


def test_CET1(make_duplicate_record):
    """The type of the Certificate must be unique."""

    duplicate = make_duplicate_record(factories.CertificateTypeFactory)

    with pytest.raises(BusinessRuleViolation):
        business_rules.CET1(duplicate.transaction).validate(duplicate)


def test_CET2(delete_record):
    """The Certificate type cannot be deleted if it is used in a Certificate."""

    certificate = factories.CertificateFactory.create()

    with pytest.raises(BusinessRuleViolation):
        business_rules.CET2(certificate.transaction).validate(
            delete_record(certificate.certificate_type),
        )


def test_CET3(date_ranges):
    """The start date must be less than or equal to the end date."""

    with pytest.raises(DataError):
        factories.CertificateTypeFactory.create(valid_between=date_ranges.backwards)


@pytest.mark.xfail(reason="CE2 disabled")
def test_CE2(make_duplicate_record):
    """The combination certificate type and code must be unique."""

    duplicate = make_duplicate_record(
        factories.CertificateFactory,
        identifying_fields=("sid", "certificate_type"),
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.CE2(duplicate.transaction).validate(duplicate)


def test_CE3(date_ranges):
    """The start date must be less than or equal to the end date."""

    with pytest.raises(DataError):
        factories.CertificateFactory.create(valid_between=date_ranges.backwards)


def test_CE4(date_ranges):
    """If a certificate is used in a measure condition then the validity period
    of the certificate must span the validity period of the measure."""

    condition = factories.MeasureConditionWithCertificateFactory.create(
        required_certificate__valid_between=date_ranges.starts_with_normal,
        dependent_measure__valid_between=date_ranges.normal,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.CE4(condition.transaction).validate(
            condition.required_certificate,
        )


def test_CE5(delete_record):
    """The certificate cannot be deleted if it is used in a measure
    condition."""

    condition = factories.MeasureConditionWithCertificateFactory.create()

    with pytest.raises(BusinessRuleViolation):
        business_rules.CE5(condition.transaction).validate(
            delete_record(condition.required_certificate),
        )


def test_CE6_one_description_mandatory():
    """At least one description record is mandatory."""
    certificate = factories.CertificateFactory.create()
    with pytest.raises(BusinessRuleViolation):
        # certificate created without description
        business_rules.CE6(certificate.transaction).validate(certificate)


def test_CE6_first_description_must_have_same_start_date(date_ranges):
    """The start date of the first description period must be equal to the start
    date of the certificate."""

    description = factories.CertificateDescriptionFactory.create(
        described_certificate__valid_between=date_ranges.no_end,
        valid_between=date_ranges.later,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.CE6(description.transaction).validate(
            description.described_certificate,
        )


def test_CE6_start_dates_cannot_match():
    """No two associated description periods for the same certificate and
    language may have the same start date."""

    existing = factories.CertificateDescriptionFactory.create()
    new_description = factories.CertificateDescriptionFactory.create(
        described_certificate=existing.described_certificate,
        valid_between=existing.valid_between,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.CE6(new_description.transaction).validate(
            existing.described_certificate,
        )


def test_CE6_certificate_validity_period_must_span_description(date_ranges):
    """The validity period of the certificate must span the validity period of
    the certificate description."""

    description = factories.CertificateDescriptionFactory.create(
        described_certificate__valid_between=date_ranges.normal,
        valid_between=date_ranges.overlap_normal,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.CE6(description.transaction).validate(
            description.described_certificate,
        )


def test_CE7(date_ranges):
    """The validity period of the certificate type must span the validity period
    of the certificate."""

    with pytest.raises(BusinessRuleViolation):
        certificate = factories.CertificateFactory.create(
            certificate_type__valid_between=date_ranges.normal,
            valid_between=date_ranges.overlap_normal,
        )
        business_rules.CE7(certificate.transaction).validate(certificate)


@pytest.mark.xfail(reason="rule disabled")
def test_certificate_description_periods_cannot_overlap(date_ranges):
    """Ensure validity periods for descriptions with a given SID cannot
    overlap."""
    # XXX All versions of a description will have the same SID. Won't this prevent
    # updates and deletes?

    existing = factories.CertificateDescriptionFactory.create(
        valid_between=date_ranges.normal,
    )
    description = factories.CertificateDescriptionFactory.create(
        described_certificate=existing.described_certificate,
        sid=existing.sid,
        valid_between=date_ranges.overlap_normal,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.NoOverlappingDescriptions(description.transaction).validate(
            description,
        )
