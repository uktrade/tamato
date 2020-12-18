import pytest
from django.core.exceptions import ValidationError
from django.db import DataError
from django.db import IntegrityError

from certificates import business_rules
from common.tests import factories


pytestmark = pytest.mark.django_db


def test_CET1(make_duplicate_record):
    """The type of the Certificate must be unique."""

    duplicate = make_duplicate_record(factories.CertificateTypeFactory)

    with pytest.raises(ValidationError):
        business_rules.CET1().validate(duplicate)


def test_CET2(delete_record):
    """The Certificate type cannot be deleted if it is used in a Certificate."""

    certificate = factories.CertificateFactory()

    with pytest.raises(ValidationError):
        business_rules.CET2().validate(delete_record(certificate.certificate_type))


def test_CET3(date_ranges):
    """The start date must be less than or equal to the end date."""

    with pytest.raises(DataError):
        factories.CertificateTypeFactory.create(valid_between=date_ranges.backwards)


def test_CE2(make_duplicate_record):
    """The combination certificate type and code must be unique."""

    duplicate = make_duplicate_record(
        factories.CertificateFactory, identifying_fields=("sid", "certificate_type")
    )

    with pytest.raises(ValidationError):
        business_rules.CE2().validate(duplicate)


def test_CE3(date_ranges):
    """The start date must be less than or equal to the end date."""

    with pytest.raises(DataError):
        factories.CertificateFactory.create(valid_between=date_ranges.backwards)


def test_CE4(date_ranges):
    """If a certificate is used in a measure condition then the validity period of the certificate
    must span the validity period of the measure.
    """

    condition = factories.MeasureConditionWithCertificateFactory(
        required_certificate__valid_between=date_ranges.starts_with_normal,
        dependent_measure__valid_between=date_ranges.normal,
    )

    with pytest.raises(ValidationError):
        business_rules.CE4().validate(condition.required_certificate)


def test_CE5(delete_record):
    """The certificate cannot be deleted if it is used in a measure condition."""

    condition = factories.MeasureConditionWithCertificateFactory()

    with pytest.raises(ValidationError):
        business_rules.CE5().validate(delete_record(condition.required_certificate))


def test_CE6_one_description_mandatory():
    """At least one description record is mandatory."""

    with pytest.raises(ValidationError):
        # certificate created without description
        business_rules.CE6().validate(factories.CertificateFactory())


def test_CE6_first_description_must_have_same_start_date(date_ranges):
    """The start date of the first description period must be equal to the start date of
    the certificate.
    """

    description = factories.CertificateDescriptionFactory(
        described_certificate__valid_between=date_ranges.no_end,
        valid_between=date_ranges.later,
    )

    with pytest.raises(ValidationError):
        business_rules.CE6().validate(description.described_certificate)


def test_CE6_start_dates_cannot_match():
    """No two associated description periods for the same certificate and language may
    have the same start date.
    """

    existing = factories.CertificateDescriptionFactory()
    factories.CertificateDescriptionFactory(
        described_certificate=existing.described_certificate,
        valid_between=existing.valid_between,
    )

    with pytest.raises(ValidationError):
        business_rules.CE6().validate(existing.described_certificate)


def test_CE6_certificate_validity_period_must_span_description(date_ranges):
    """The validity period of the certificate must span the validity period of the
    certificate description.
    """

    description = factories.CertificateDescriptionFactory(
        described_certificate__valid_between=date_ranges.normal,
        valid_between=date_ranges.overlap_normal,
    )

    with pytest.raises(ValidationError):
        business_rules.CE6().validate(description.described_certificate)


def test_CE7(date_ranges):
    """The validity period of the certificate type must span the validity period of the
    certificate.
    """

    with pytest.raises(ValidationError):
        business_rules.CE7().validate(
            factories.CertificateFactory(
                certificate_type__valid_between=date_ranges.normal,
                valid_between=date_ranges.overlap_normal,
            )
        )


def test_certificate_description_periods_cannot_overlap(date_ranges):
    """Ensure validity periods for descriptions with a given SID cannot overlap."""
    # XXX All versions of a description will have the same SID. Won't this prevent
    # updates and deletes?

    existing = factories.CertificateDescriptionFactory(valid_between=date_ranges.normal)
    description = factories.CertificateDescriptionFactory(
        described_certificate=existing.described_certificate,
        sid=existing.sid,
        valid_between=date_ranges.overlap_normal,
    )

    with pytest.raises(ValidationError):
        business_rules.NoOverlappingDescriptions().validate(description)


def test_certificate_description_period_must_be_adjacent_to_predecessor(date_ranges):
    """Ensure validity periods for successive descriptions must be adjacent."""

    predecessor = factories.CertificateDescriptionFactory(
        valid_between=date_ranges.normal,
    )
    predecessor = factories.CertificateDescriptionFactory(
        sid=predecessor.sid,
        predecessor=predecessor,
        described_certificate=predecessor.described_certificate,
        valid_between=date_ranges.adjacent_later,
    )
    assert business_rules.ContiguousDescriptions().validate(predecessor) is None

    description = factories.CertificateDescriptionFactory(
        sid=predecessor.sid,
        predecessor=predecessor,
        described_certificate=predecessor.described_certificate,
        valid_between=date_ranges.adjacent_even_later,
    )
    with pytest.raises(ValidationError):
        business_rules.ContiguousDescriptions().validate(description)
