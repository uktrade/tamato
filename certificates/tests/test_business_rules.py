import pytest
from django.db import DataError

from certificates import business_rules
from common.business_rules import BusinessRuleViolation
from common.tests import factories
from common.validators import UpdateType

pytestmark = pytest.mark.django_db


def test_CET1(assert_handles_duplicates):
    """The type of the Certificate must be unique."""

    assert_handles_duplicates(
        factories.CertificateTypeFactory,
        business_rules.CET1,
    )


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
def test_CE2(assert_handles_duplicates):
    """The combination certificate type and code must be unique."""

    assert_handles_duplicates(
        factories.CertificateFactory,
        business_rules.CE2,
        identifying_fields=("sid", "certificate_type"),
    )


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
        validity_start=date_ranges.later.lower,
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
        validity_start=existing.validity_start,
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
        validity_start=date_ranges.overlap_normal.lower,
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


def test_CertificateUpdateValidity_first_update_must_be_Create():
    """The first update to a certificate must be of type Create."""
    certificate = factories.CertificateFactory.create(update_type=UpdateType.DELETE)

    with pytest.raises(BusinessRuleViolation):
        business_rules.UpdateValidity(certificate.transaction).validate(certificate)


def test_CertificateUpdateValidity_later_updates_must_not_be_Create():
    """Updates to a Certificate after the first update must not be of type
    Create."""
    first_certificate = factories.CertificateFactory.create()
    second_certificate = factories.CertificateFactory.create(
        update_type=UpdateType.CREATE,
        version_group=first_certificate.version_group,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.UpdateValidity(second_certificate.transaction).validate(
            second_certificate,
        )


def test_CertificateUpdateValidity_must_not_update_after_Delete():
    """There must not be updates to a Certificate version group after an update
    of type Delete."""
    first_certificate = factories.CertificateFactory.create(
        update_type=UpdateType.DELETE,
    )
    second_certificate = factories.CertificateFactory.create(
        update_type=UpdateType.UPDATE,
        version_group=first_certificate.version_group,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.UpdateValidity(second_certificate.transaction).validate(
            second_certificate,
        )


def test_CertificateUpdateValidity_only_one_version_per_transaction():
    """The transaction must contain no more than one update to each Certificate
    version group."""
    first_certificate = factories.CertificateFactory.create()
    second_certificate = factories.CertificateFactory.create(
        update_type=UpdateType.UPDATE,
        version_group=first_certificate.version_group,
        transaction=first_certificate.transaction,
    )

    with pytest.raises(BusinessRuleViolation):
        business_rules.UpdateValidity(second_certificate.transaction).validate(
            second_certificate,
        )
